import json
import os
import time
import requests

from confluent_kafka import Producer, Consumer
from pathlib import Path
from dotenv import load_dotenv

# ------------------
# Env / paths
# ------------------

PROJECT_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(PROJECT_ROOT / ".env")

STATUS_URL = "https://lichess.org/api/users/status"
CURRENT_GAME_URL = "https://lichess.org/api/user/{username}/current-game"

PROFILE_INPUT_TOPIC = os.getenv("TOPIC_PROFILE_IN", "player_profile_input")

# ------------------
# Kafka config
# ------------------

def read_config(path: str) -> dict:
    config = {}
    with open(path) as fh:
        for line in fh:
            line = line.strip()
            if line and not line.startswith("#"):
                k, v = line.split("=", 1)
                config[k.strip()] = v.strip()
    return config

# ------------------
# Lichess helpers
# ------------------

def lichess_user_status(username: str, timeout_s: int = 10) -> dict:
    r = requests.get(
        STATUS_URL,
        params={"ids": username, "withGameIds": "true"},
        headers={"Accept": "application/json"},
        timeout=timeout_s,
    )
    r.raise_for_status()
    data = r.json()
    return data[0] if data else {}


def lichess_current_game(username: str, timeout_s: int = 10) -> dict | None:
    r = requests.get(
        CURRENT_GAME_URL.format(username=username),
        params={"moves": "true", "clocks": "true", "opening": "true"},
        headers={"Accept": "application/json"},
        timeout=timeout_s,
    )
    if r.status_code == 404:
        return None
    r.raise_for_status()
    return r.json()


def split_moves(moves_str: str | None) -> list[str]:
    return moves_str.strip().split() if moves_str else []


# ------------------
# Kafka helpers
# ------------------

def delivery_report(err, msg):
    if err:
        print(f"[DELIVERY_FAILED] {err}", flush=True)
    else:
        print(
            f"[DELIVERED] topic={msg.topic()} partition={msg.partition()} offset={msg.offset()}",
            flush=True,
        )


def wait_for_profile(config: dict) -> dict:
    consumer = Consumer({
        **config,
        "group.id": f"lichess-profile-consumer-v5",
        "auto.offset.reset": "latest",
    })

    consumer.subscribe([PROFILE_INPUT_TOPIC])
    #consumer.poll(5.0)
    time.sleep(3)
    print("[WAIT] Waiting for profile message...", flush=True)

    while True:
        msg = consumer.poll(1.0)
        if msg is None:
            continue
        if msg.error():
            raise RuntimeError(msg.error())

        profile_event = json.loads(msg.value())
        print(f"[PROFILE_RECEIVED] username={profile_event['username']}", flush=True)
        return profile_event


# ------------------
# Main producer logic
# ------------------

def produce_lichess_stream(
    username: str,
    profile: dict,
    topic_player_profile: str,
    topic_live_moves: str,
    topic_session_events: str,
    config: dict,
    poll_seconds: float = 1.0,
):
    producer = Producer(config)

    last_game_id = None
    last_moves: list[str] = []
    profile_sent = False

    print(f"[START] Tracking user={username}", flush=True)

    while True:
        try:
            status = lichess_user_status(username)
            playing_id = status.get("playingId")
            playing = bool(status.get("playing"))

            if not playing or not playing_id:
                if last_game_id:
                    end_payload = {
                        "event": "session_end",
                        "username": username,
                        "game_id": last_game_id,
                        "ts": int(time.time() * 1000),
                    }
                    producer.produce(
                        topic_session_events,
                        key=last_game_id,
                        value=json.dumps(end_payload),
                        callback=delivery_report,
                    )
                    producer.flush()
                    print(f"[SESSION_END] {last_game_id}", flush=True)

                last_game_id = None
                last_moves = []
                profile_sent = False
                time.sleep(2)
                continue

            if playing_id != last_game_id:
                last_game_id = playing_id
                last_moves = []
                profile_sent = False

                start_payload = {
                    "event": "session_start",
                    "username": username,
                    "game_id": playing_id,
                    "ts": int(time.time() * 1000),
                }
                producer.produce(
                    topic_session_events,
                    key=playing_id,
                    value=json.dumps(start_payload),
                    callback=delivery_report,
                )
                producer.flush()
                print(f"[SESSION_START] {playing_id}", flush=True)

            snap = lichess_current_game(username)
            if snap is None:
                time.sleep(1)
                continue

            # Emit REAL profile (from FastAPI) once per game
            if not profile_sent:
                producer.produce(
                    topic_player_profile,
                    key=last_game_id,
                    value=json.dumps({
                        "event": "player_profile", # Updated the key.
                        "game_id": last_game_id,
                        "username": username,
                        "profile": profile,
                    }),
                    callback=delivery_report,
                )
                producer.flush()
                profile_sent = True
                print(f"[PROFILE_EMITTED] game_id={last_game_id}", flush=True)

            moves = split_moves(snap.get("moves"))
            if len(moves) > len(last_moves):
                new_moves = moves[len(last_moves):]
                for idx, uci in enumerate(new_moves, start=len(last_moves) + 1):
                    move_payload = {
                        "event": "move",
                        "game_id": last_game_id,
                        "username": username, 
                        "move_number": idx,
                        "snap": snap, # Changed UCI to Snap.
                        "ts": int(time.time() * 1000),
                    }
                    producer.produce(
                        topic_live_moves,
                        key=last_game_id,
                        value=json.dumps(move_payload),
                        callback=delivery_report,
                    )
                    print(f"[MOVE] {last_game_id} #{idx} {uci}", flush=True)

                producer.poll(0)
                last_moves = moves

            producer.poll(0)
            time.sleep(poll_seconds)

        except Exception as e:
            print(f"[ERROR] {e}", flush=True)
            time.sleep(2)


# ------------------
# Entry point
# ------------------

def main():
    config_path = Path(os.getenv("KAFKA_CONFIG", str(PROJECT_ROOT / "client.properties")))
    config = read_config(str(config_path))

    topic_player_profile = os.getenv("TOPIC_PROFILE_IN", "player_profile_input")
    topic_live_moves = os.getenv("TOPIC_LIVE_MOVES", "live_moves")
    topic_session_events = os.getenv("TOPIC_SESSION_EVENTS", "session_events")
    poll_seconds = float(os.getenv("POLL_SECONDS", "1.0"))

    profile_event = wait_for_profile(config)

    username = profile_event["username"]
    profile = profile_event["profile"]

    print(profile)

    produce_lichess_stream(
        username=username,
        profile=profile,
        topic_player_profile=topic_player_profile,
        topic_live_moves=topic_live_moves,
        topic_session_events=topic_session_events,
        config=config,
        poll_seconds=poll_seconds,
    )


if __name__ == "__main__":
    main()
