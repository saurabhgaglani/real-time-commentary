import json
import os
import time
import requests

from confluent_kafka import Producer, Consumer
from pathlib import Path
from dotenv import load_dotenv

# Import health server for Cloud Run compatibility
from backend.health_server import start_health_server

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
    """Wait for a profile message from Kafka."""
    import time
    
    # Use fixed consumer group with LATEST offset to only read new messages
    consumer_group = "lichess-profile-consumer-fixed"
    
    print(f"[KAFKA] Creating consumer with group: {consumer_group}", flush=True)
    
    consumer = Consumer({
        **config,
        "group.id": consumer_group,
        "auto.offset.reset": "latest",  # Only read NEW messages
        "enable.auto.commit": True,
        "auto.commit.interval.ms": 1000,
    })

    consumer.subscribe([PROFILE_INPUT_TOPIC])
    
    print(f"[KAFKA] ✓ Consumer created successfully", flush=True)
    print(f"[KAFKA] ✓ Subscribed to topic: {PROFILE_INPUT_TOPIC}", flush=True)
    print(f"[KAFKA] ✓ Consumer group: {consumer_group}", flush=True)
    print(f"[KAFKA] ✓ Offset reset: latest", flush=True)
    print(f"[KAFKA] Kafka stream is UP and RUNNING", flush=True)
    print(f"[WAIT] Waiting for NEW profile messages from UI...", flush=True)
    print("[INFO] Please use the UI to analyze a user and send a profile.", flush=True)

    poll_count = 0
    while True:
        msg = consumer.poll(1.0)
        poll_count += 1
        
        # Log every 30 seconds to show we're still alive
        if poll_count % 30 == 0:
            print(f"[KAFKA] Still polling (count: {poll_count})... Kafka stream active", flush=True)
        
        if msg is None:
            continue
        if msg.error():
            print(f"[KAFKA ERROR] {msg.error()}", flush=True)
            raise RuntimeError(msg.error())

        # Log ALL messages received (before event type filtering)
        print(f"[KAFKA] Message received: topic={msg.topic()}, partition={msg.partition()}, offset={msg.offset()}", flush=True)
        
        profile_event = json.loads(msg.value())
        
        # Log the event type for every message
        event_type = profile_event.get('event', 'UNKNOWN')
        print(f"[KAFKA] Event type: {event_type}", flush=True)
        
        # Filter for player_profile events only
        if event_type != 'player_profile':
            print(f"[SKIP] Ignoring event type: {event_type}", flush=True)
            continue
        
        # Verify it has the required fields
        if 'username' not in profile_event:
            print(f"[SKIP] Profile event missing username field", flush=True)
            continue
        
        print(f"[PROFILE_RECEIVED] ✓ username={profile_event['username']}", flush=True)
        consumer.close()
        print(f"[KAFKA] Consumer closed after receiving profile", flush=True)
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
    print(f"[PRODUCER] Creating Kafka producer...", flush=True)
    producer = Producer(config)
    print(f"[PRODUCER] ✓ Kafka producer created", flush=True)

    last_game_id = None
    last_moves: list[str] = []
    profile_sent = False

    print(f"[START] ✓ Tracking user={username}", flush=True)
    print(f"[START] Will publish to topics:", flush=True)
    print(f"  - Profile: {topic_player_profile}", flush=True)
    print(f"  - Moves: {topic_live_moves}", flush=True)
    print(f"  - Sessions: {topic_session_events}", flush=True)

    loop_count = 0
    while True:
        try:
            loop_count += 1
            
            # Log every 60 seconds to show we're still tracking
            if loop_count % 60 == 0:
                print(f"[TRACKING] Still tracking {username} (loop: {loop_count})...", flush=True)
            
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
                    print(f"[SESSION_END] ✓ {last_game_id}", flush=True)

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
                print(f"[SESSION_START] ✓ {playing_id}", flush=True)

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
                print(f"[PROFILE_EMITTED] ✓ game_id={last_game_id}", flush=True)

            moves = split_moves(snap.get("moves"))
            if len(moves) > len(last_moves):
                new_moves = moves[len(last_moves):]
                #for idx, uci in enumerate(new_moves, start=len(last_moves) + 1):
                move_payload = {
                    "event": "move",
                    "game_id": last_game_id,
                    "username": username, 
                    "move_number": len(moves),
                    "snap": snap, # Changed UCI to Snap.
                    "ts": int(time.time() * 1000),
                }
                producer.produce(
                    topic_live_moves,
                    key=last_game_id,
                    value=json.dumps(move_payload),
                    callback=delivery_report,
                )
                print(f"[MOVE] ✓ {last_game_id} #{len(moves)} {moves[-1]}", flush=True)

                producer.poll(0)
                last_moves = moves

            producer.poll(0)
            time.sleep(poll_seconds)

        except KeyboardInterrupt:
            print(f"\n[SHUTDOWN] Tracking interrupted for {username}", flush=True)
            raise
        except Exception as e:
            print(f"[ERROR] Tracking error for {username}: {e}", flush=True)
            import traceback
            traceback.print_exc()
            time.sleep(2)


# ------------------
# Entry point
# ------------------

def main():
    # Start health check server for Cloud Run (runs in background thread)
    start_health_server(port=8080)
    
    print("=" * 60, flush=True)
    print("PRODUCER SERVICE STARTING", flush=True)
    print("=" * 60, flush=True)
    print(f"[STARTUP] PID: {os.getpid()}", flush=True)
    print(f"[STARTUP] Script: backend/producer_lichess.py", flush=True)
    print(f"[STARTUP] Time: {time.strftime('%Y-%m-%d %H:%M:%S UTC', time.gmtime())}", flush=True)
    
    config_path = Path(os.getenv("KAFKA_CONFIG", str(PROJECT_ROOT / "client.properties")))
    print(f"[CONFIG] Kafka config path: {config_path}", flush=True)
    print(f"[CONFIG] Config exists: {config_path.exists()}", flush=True)
    
    try:
        config = read_config(str(config_path))
        print(f"[KAFKA] Successfully loaded config with {len(config)} entries", flush=True)
        print(f"[KAFKA] Bootstrap servers: {config.get('bootstrap.servers', 'NOT SET')}", flush=True)
    except Exception as e:
        print(f"[FATAL] Failed to load Kafka config: {e}", flush=True)
        raise

    topic_player_profile = os.getenv("TOPIC_PROFILE_IN", "player_profile_input")
    topic_live_moves = os.getenv("TOPIC_LIVE_MOVES", "live_moves")
    topic_session_events = os.getenv("TOPIC_SESSION_EVENTS", "session_events")
    poll_seconds = float(os.getenv("POLL_SECONDS", "1.0"))
    
    print(f"[CONFIG] Profile topic: {topic_player_profile}", flush=True)
    print(f"[CONFIG] Moves topic: {topic_live_moves}", flush=True)
    print(f"[CONFIG] Session topic: {topic_session_events}", flush=True)
    print(f"[CONFIG] Poll interval: {poll_seconds}s", flush=True)
    print("=" * 60, flush=True)

    try:
        profile_event = wait_for_profile(config)

        username = profile_event["username"]
        profile = profile_event["profile"]

        print(f"[PROFILE] Received profile for: {username}", flush=True)
        print(f"[TRACKING] Starting game tracking for: {username}", flush=True)

        produce_lichess_stream(
            username=username,
            profile=profile,
            topic_player_profile=topic_player_profile,
            topic_live_moves=topic_live_moves,
            topic_session_events=topic_session_events,
            config=config,
            poll_seconds=poll_seconds,
        )
    except KeyboardInterrupt:
        print("\n[SHUTDOWN] Received interrupt signal", flush=True)
        print(f"[SHUTDOWN] Producer service stopped at {time.strftime('%Y-%m-%d %H:%M:%S UTC', time.gmtime())}", flush=True)
    except Exception as e:
        print(f"[FATAL] Producer crashed: {e}", flush=True)
        import traceback
        traceback.print_exc()
        raise


if __name__ == "__main__":
    main()
