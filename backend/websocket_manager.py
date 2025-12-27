"""
WebSocket Manager for real-time commentary delivery.

This module manages WebSocket connections and bridges Kafka audio events
to connected clients.
websocket_manager.py
"""

from fastapi import WebSocket
from typing import Dict, List
import logging
import json
import asyncio
from confluent_kafka import Consumer, KafkaError
from pathlib import Path
import os

logger = logging.getLogger(__name__)


class ConnectionManager:
    """Manages active WebSocket connections for commentary delivery."""
    
    def __init__(self):
        # Map of game_id -> list of WebSocket connections
        self.active_connections: Dict[str, List[WebSocket]] = {}
        logger.info("ConnectionManager initialized")
    
    async def connect(self, websocket: WebSocket, game_id: str):
        """
        Accept and register a new WebSocket connection.
        
        Args:
            websocket: The WebSocket connection to register
            game_id: The game ID this connection is subscribing to
        """
        await websocket.accept()
        
        if game_id not in self.active_connections:
            self.active_connections[game_id] = []
        
        self.active_connections[game_id].append(websocket)
        logger.info(f"Client connected to game {game_id}. Total connections for this game: {len(self.active_connections[game_id])}")
    
    async def disconnect(self, websocket: WebSocket, game_id: str):
        """
        Remove a WebSocket connection.
        
        Args:
            websocket: The WebSocket connection to remove
            game_id: The game ID this connection was subscribed to
        """
        if game_id in self.active_connections:
            if websocket in self.active_connections[game_id]:
                self.active_connections[game_id].remove(websocket)
                logger.info(f"Client disconnected from game {game_id}. Remaining connections: {len(self.active_connections[game_id])}")
            
            # Clean up empty game_id entries
            if len(self.active_connections[game_id]) == 0:
                del self.active_connections[game_id]
                logger.info(f"No more connections for game {game_id}, removed from active connections")
    
    async def send_audio_event(self, game_id: str, message: dict):
        """
        Send audio event to all clients watching a specific game.
        
        Args:
            game_id: The game ID to send the message to
            message: The audio event message to send
        """
        if game_id not in self.active_connections:
            logger.debug(f"No active connections for game {game_id}, skipping audio event for move {message.get('move_number')}")
            return
        
        # Create a copy of the connection list to avoid modification during iteration
        connections = self.active_connections[game_id].copy()
        dead_connections = []
        
        logger.info(f"Sending audio event to {len(connections)} client(s) for game {game_id}, move {message.get('move_number')}")
        
        for websocket in connections:
            try:
                await websocket.send_json(message)
                logger.debug(f"Successfully sent audio event to client for game {game_id}")
            except Exception as e:
                logger.error(f"Failed to send message to client for game {game_id}: {e}")
                dead_connections.append(websocket)
        
        # Remove dead connections
        for websocket in dead_connections:
            await self.disconnect(websocket, game_id)
    
    async def broadcast(self, message: dict):
        """
        Send message to all connected clients across all games.
        
        Args:
            message: The message to broadcast
        """
        for game_id in list(self.active_connections.keys()):
            await self.send_audio_event(game_id, message)


class KafkaWebSocketBridge:
    """Consumes Kafka messages and sends them to WebSocket clients."""
    
    def __init__(self, connection_manager: ConnectionManager, kafka_config_path: Path, topic: str):
        """
        Initialize the Kafka-WebSocket bridge.
        
        Args:
            connection_manager: The ConnectionManager instance to use
            kafka_config_path: Path to Kafka configuration file
            topic: Kafka topic to consume from
        """
        self.connection_manager = connection_manager
        self.kafka_config_path = kafka_config_path
        self.topic = topic
        self.consumer = None
        self.running = False
        self.processed_events = set()  # Track processed events to avoid duplicates
        logger.info(f"KafkaWebSocketBridge initialized for topic: {topic}")
    
    def _load_kafka_config(self) -> dict:
        """Load Kafka configuration from properties file."""
        config = {}
        with open(self.kafka_config_path) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#"):
                    k, v = line.split("=", 1)
                    config[k] = v
        
        # Add consumer-specific configuration
        config["group.id"] = "websocket-commentary-consumer-v1"  # Versioned group
        config["auto.offset.reset"] = "latest"  # Only new messages
        config["enable.auto.commit"] = True
        config["auto.commit.interval.ms"] = 1000  # Commit offsets frequently
        
        return config
    
    async def start_consuming(self):
        """Start consuming from Kafka topic in background."""
        try:
            kafka_config = self._load_kafka_config()
            logger.info(f"Kafka config loaded: {kafka_config.get('bootstrap.servers')}, group: {kafka_config.get('group.id')}")
            
            self.consumer = Consumer(kafka_config)
            self.consumer.subscribe([self.topic])
            self.running = True
            
            logger.info(f"Started consuming from topic: {self.topic}")
            logger.info(f"Waiting for messages on topic: {self.topic}...")
            
            # Run consumer in background
            poll_count = 0
            while self.running:
                # Poll with timeout to allow checking self.running
                msg = self.consumer.poll(timeout=1.0)
                poll_count += 1
                
                # Log every 30 seconds to show we're still polling
                if poll_count % 30 == 0:
                    logger.info(f"Still polling topic {self.topic}... (no messages yet)")
                
                if msg is None:
                    # No message, continue polling
                    await asyncio.sleep(0.1)
                    continue
                
                if msg.error():
                    if msg.error().code() == KafkaError._PARTITION_EOF:
                        logger.debug(f"Reached end of partition for {msg.topic()}")
                    else:
                        logger.error(f"Kafka consumer error: {msg.error()}")
                    continue
                
                # Process the message
                try:
                    event = json.loads(msg.value().decode("utf-8"))
                    event_type = event.get('event')
                    
                    # Only process commentary_audio events, skip all others
                    if event_type != 'commentary_audio':
                        logger.debug(f"Skipping non-audio event: {event_type}")
                        await asyncio.sleep(0.1)
                        continue
                    
                    logger.info(f"Received commentary_audio event for game {event.get('game_id')}")
                    await self.process_audio_event(event)
                except Exception as e:
                    logger.error(f"Error processing audio event: {e}", exc_info=True)
                
        except Exception as e:
            logger.error(f"Fatal error in Kafka consumer: {e}", exc_info=True)
        finally:
            if self.consumer:
                self.consumer.close()
                logger.info("Kafka consumer closed")
    
    async def process_audio_event(self, event: dict):
        """
        Process and route audio event to appropriate clients.
        
        Args:
            event: The audio event from Kafka (must have event='commentary_audio')
        """
        try:
            # Double-check this is an audio event
            if event.get('event') != 'commentary_audio':
                logger.warning(f"Received non-audio event in process_audio_event: {event.get('event')}")
                return
            
            game_id = event.get("game_id")
            move_number = event.get("move_number")
            audio_url = event.get("audio_url")
            created_at_ms = event.get("created_at_ms")
            
            if not game_id:
                logger.warning("Received audio event without game_id, skipping")
                return
            
            # Create unique event ID for deduplication
            event_id = f"{game_id}:{move_number}:{created_at_ms}"
            
            logger.info(f"[DEDUP CHECK] Event ID: {event_id}")
            
            # Check if we've already processed this event
            if event_id in self.processed_events:
                logger.warning(f"[DUPLICATE DETECTED] Skipping duplicate audio event: {event_id}")
                return
            
            logger.info(f"[NEW EVENT] Processing new audio event: {event_id}")
            
            # Mark as processed
            self.processed_events.add(event_id)
            
            # Limit the size of processed_events set (keep last 1000)
            if len(self.processed_events) > 1000:
                # Remove oldest half
                self.processed_events = set(list(self.processed_events)[-500:])
            
            logger.info(f"Processing audio event for game {game_id}, move {move_number}, audio: {audio_url}")
            
            # Send to all clients watching this game
            await self.connection_manager.send_audio_event(game_id, event)
            
        except Exception as e:
            logger.error(f"Error in process_audio_event: {e}", exc_info=True)
    
    async def stop(self):
        """Stop the Kafka consumer gracefully."""
        logger.info("Stopping Kafka consumer...")
        self.running = False
