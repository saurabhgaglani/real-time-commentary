import json
import os
from datetime import datetime
from pathlib import Path
import sys
from confluent_kafka import Producer
from dotenv import load_dotenv

# ------------------
# Setup
# ------------------

PROJECT_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(PROJECT_ROOT / ".env")

KAFKA_CONFIG_PATH = Path(
    os.getenv("KAFKA_CONFIG", str(PROJECT_ROOT / "client.properties"))
)
PROFILE_TOPIC = os.getenv("TOPIC_PROFILE_IN", "player_profile_input")


def load_kafka_config(path: Path) -> dict:
    config = {}
    with open(path) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#"):
                k, v = line.split("=", 1)
                config[k] = v
    return config


# ------------------
# Main
# ------------------

def main():
    username = sys.argv[1] if len(sys.argv) > 1 else "CleverKenkz"

    kafka_config = load_kafka_config(KAFKA_CONFIG_PATH)
    producer = Producer(kafka_config)

    # Minimal stub profile (enough to unblock downstream logic)
    profile = {
        "style": "balanced",
        "risk_tolerance": "medium",
        "preferred_openings": ["Italian Game", "Sicilian Defense"],
    }

    event = {
        "event": "player_profile",
        "username": username,
        "game_id": "TEST_GAME_ID",
        "profile": profile,
        "ts": int(datetime.utcnow().timestamp() * 1000),
    }

    producer.produce(
        topic=PROFILE_TOPIC,
        key=username,
        value=json.dumps(event).encode("utf-8"),
    )
    producer.flush()

    print(f"[TEST_PUBLISH] profile sent for username={username}")


if __name__ == "__main__":
    main()
