"""
Test script to verify Kafka consumer can read from commentary_audio topic
"""
import json
import os
from pathlib import Path
from confluent_kafka import Consumer
from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(PROJECT_ROOT / ".env")

def load_kafka_config(path: Path) -> dict:
    config = {}
    with open(path) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#"):
                k, v = line.split("=", 1)
                config[k] = v
    
    # Add consumer-specific configuration
    config["group.id"] = "test-websocket-consumer"
    config["auto.offset.reset"] = "earliest"  # Read from beginning for testing
    config["enable.auto.commit"] = True
    
    return config

def main():
    KAFKA_CONFIG_PATH = Path(os.getenv("KAFKA_CONFIG", str(PROJECT_ROOT / "client.properties")))
    COMMENTARY_AUDIO_TOPIC = os.getenv("TOPIC_COMMENTARY_AUDIO", "chess_stream")  # Changed default to chess_stream
    
    print(f"Loading Kafka config from: {KAFKA_CONFIG_PATH}")
    print(f"Consuming from topic: {COMMENTARY_AUDIO_TOPIC}")
    print(f"Filtering for event='commentary_audio' only")
    
    kafka_config = load_kafka_config(KAFKA_CONFIG_PATH)
    print(f"Bootstrap servers: {kafka_config.get('bootstrap.servers')}")
    print(f"Group ID: {kafka_config.get('group.id')}")
    
    consumer = Consumer(kafka_config)
    consumer.subscribe([COMMENTARY_AUDIO_TOPIC])
    
    print("\nWaiting for audio events... (Press Ctrl+C to stop)")
    print("-" * 60)
    
    try:
        message_count = 0
        audio_event_count = 0
        while True:
            msg = consumer.poll(timeout=1.0)
            
            if msg is None:
                continue
            
            if msg.error():
                print(f"Error: {msg.error()}")
                continue
            
            message_count += 1
            event = json.loads(msg.value().decode("utf-8"))
            event_type = event.get('event')
            
            # Only show commentary_audio events
            if event_type == 'commentary_audio':
                audio_event_count += 1
                print(f"\n[Audio Event #{audio_event_count}] (Total messages: {message_count})")
                print(f"  Event: {event_type}")
                print(f"  Game ID: {event.get('game_id')}")
                print(f"  Move: {event.get('move_number')}")
                print(f"  Latest Move: {event.get('latest_move')}")
                print(f"  Audio URL: {event.get('audio_url')}")
                print(f"  Commentary: {event.get('commentary_text')[:100]}...")
                print("-" * 60)
            else:
                # Just count other events
                if message_count % 10 == 0:
                    print(f"[Info] Processed {message_count} total messages, {audio_event_count} audio events")
            
    except KeyboardInterrupt:
        print("\n\nStopping consumer...")
    finally:
        consumer.close()
        print(f"Total messages received: {message_count}")
        print(f"Audio events received: {audio_event_count}")

if __name__ == "__main__":
    main()
