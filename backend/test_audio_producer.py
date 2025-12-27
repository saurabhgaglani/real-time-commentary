"""
Test script to produce fake audio events to Kafka for UI testing.
This will send commentary_audio events using existing audio files.
"""
import json
import os
import time
from pathlib import Path
from confluent_kafka import Producer
from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(PROJECT_ROOT / ".env")

def read_config(path: str) -> dict:
    config = {}
    with open(path) as fh:
        for line in fh:
            line = line.strip()
            if line and not line.startswith("#"):
                k, v = line.split("=", 1)
                config[k.strip()] = v.strip()
    return config

def delivery_report(err, msg):
    if err:
        print(f"[DELIVERY_FAILED] {err}", flush=True)
    else:
        print(f"[DELIVERED] topic={msg.topic()} partition={msg.partition()} offset={msg.offset()}", flush=True)

def get_audio_files():
    """Get list of audio files from the audio directory."""
    audio_dir = PROJECT_ROOT / "audio"
    if not audio_dir.exists():
        print(f"Audio directory not found: {audio_dir}")
        return []
    
    audio_files = list(audio_dir.glob("*.mp3"))
    return audio_files

def main():
    # Load config
    config_path = Path(os.getenv("KAFKA_CONFIG", str(PROJECT_ROOT / "client.properties")))
    config = read_config(str(config_path))
    
    topic = os.getenv("TOPIC_COMMENTARY_AUDIO", "chess_stream")
    
    print("=" * 60)
    print("Audio Event Test Producer")
    print("=" * 60)
    print(f"Topic: {topic}")
    print(f"Config: {config_path}")
    print()
    
    # Get audio files
    audio_files = get_audio_files()
    if not audio_files:
        print("No audio files found in audio/ directory!")
        print("Please generate some audio first using consumer_commentary.py")
        return
    
    print(f"Found {len(audio_files)} audio file(s):")
    for i, f in enumerate(audio_files, 1):
        print(f"  {i}. {f.name}")
    print()
    
    # Get test game_id
    game_id = input("Enter a test game_id (or press Enter for 'test_game_123'): ").strip()
    if not game_id:
        game_id = "test_game_123"
    
    print(f"\nUsing game_id: {game_id}")
    print(f"Make sure your frontend is connected to this game_id!")
    print()
    
    # Create producer
    producer = Producer(config)
    
    # Send events for each audio file
    print("Sending audio events...")
    print("-" * 60)
    
    for i, audio_file in enumerate(audio_files, 1):
        # Create audio event
        audio_url = f"/audio/{audio_file.name}"
        
        event = {
            "event": "commentary_audio",
            "game_id": game_id,
            "move_number": i,
            "latest_move": f"e{i}" if i % 2 == 1 else f"d{i}",  # Fake moves
            "commentary_text": f"Test commentary for move {i} using file {audio_file.name}",
            "audio_url": audio_url,
            "created_at_ms": int(time.time() * 1000),
        }
        
        # Produce to Kafka
        producer.produce(
            topic,
            key=game_id,
            value=json.dumps(event).encode("utf-8"),
            callback=delivery_report,
        )
        
        print(f"[{i}/{len(audio_files)}] Sent: move={i}, audio={audio_file.name}")
        
        # Flush to ensure delivery
        producer.flush()
        
        # Wait a bit between messages (optional)
        time.sleep(0.5)
    
    print("-" * 60)
    print(f"\n✅ Sent {len(audio_files)} audio events to Kafka!")
    print(f"   Game ID: {game_id}")
    print(f"   Topic: {topic}")
    print()
    print("Check your UI - audio should start playing!")

if __name__ == "__main__":
    main()
