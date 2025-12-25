import json
import os
import sys
import time
import requests
from confluent_kafka import Producer

from pathlib import Path
from dotenv import load_dotenv

# Project structure:
# real-time-commentary/
# ├── client.properties
# └── backend/
#     └── producer_lichess.py

PROJECT_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(PROJECT_ROOT / ".env")  # load .env explicitly


STATUS_URL = "https://lichess.org/api/users/status"
CURRENT_GAME_URL = "https://lichess.org/api/user/{username}/current-game"


def read_config(path: str = "client.properties") -> dict:
    config = {}
    with open(path) as fh:
        for line in fh:
            line = line.strip()
            if line and not line.startswith("#"):
                k, v = line.split("=", 1)
                config[k.strip()] = v.strip()
    return config


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


def delivery_report(err, msg):
    if err is not None:
        print(f"[DELIVERY_FAILED] {err}", flush=True)
    else:
        print(
            f"[DELIVERED] topic={msg.topic()} partition={msg.partition()} offset={msg.offset()}",
            flush=True,
        )


def produce_lichess_stream(
    username: str,
    topic_player_profile: str,
    topic_live_moves: str,
    topic_session_events: str,
    config: dict,
    poll_seconds: float = 1.0,
    exit_on_game_end: bool = False,
):
    """
    Tokenless producer:
      - Uses /api/users/status to discover playingId (game_id)
      - Uses /api/user/{username}/current-game to get moves snapshot
      - Diffs moves and emits only new ones

    Produces:
      - player_profile (once per game)
      - live_moves (per new move)
      - session_events (start/end)
    """
    producer = Producer(config)

    last_game_id = None
    last_moves: list[str] = []
    profile_sent = False

    print(
        f"[START] username={username} poll={poll_seconds}s exit_on_game_end={exit_on_game_end}",
        flush=True,
    )

    while True:
        try:
            status = lichess_user_status(username)
            playing_id = status.get("playingId")
            playing = bool(status.get("playing"))

            if not playing or not playing_id:
                # If we were previously in a game, emit end once
                if last_game_id is not None:
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
                    print(f"[SESSION_END] game_id={last_game_id}", flush=True)

                    if exit_on_game_end:
                        print("[EXIT] exit_on_game_end=true", flush=True)
                        return

                last_game_id = None
                last_moves = []
                profile_sent = False
                time.sleep(2)
                continue

            game_id = playing_id

            # New game detected
            if game_id != last_game_id:
                last_game_id = game_id
                last_moves = []
                profile_sent = False

                start_payload = {
                    "event": "session_start",
                    "username": username,
                    "game_id": game_id,
                    "ts": int(time.time() * 1000),
                }
                producer.produce(
                    topic_session_events,
                    key=game_id,
                    value=json.dumps(start_payload),
                    callback=delivery_report,
                )
                producer.flush()
                print(f"[SESSION_START] game_id={game_id}", flush=True)

            # Fetch snapshot
            snap = lichess_current_game(username)
            if snap is None:
                # Sometimes status says playing but current-game 404s briefly; wait and retry
                time.sleep(1)
                continue

            # Emit player_profile once per game (placeholder; replace later)
            if not profile_sent:
                # TODO: Replace with real pre-game profile builder output.
                profile_payload = {
                    "game_id": game_id,
                    "username": username,
                    "profile": {
                        "preferred_openings": [],  # you can populate later
                        "style": "unknown",
                        "risk_tolerance": "unknown",
                    },
                }
                producer.produce(
                    topic_player_profile,
                    key=game_id,
                    value=json.dumps(profile_payload),
                    callback=delivery_report,
                )
                producer.flush()
                profile_sent = True
                print(f"[PROFILE_SENT] game_id={game_id}", flush=True)

            # Moves diff
            moves = split_moves(snap.get("moves"))
            if len(moves) > len(last_moves):
                new_moves = moves[len(last_moves) :]
                for idx, uci in enumerate(new_moves, start=len(last_moves) + 1):
                    move_payload = {
                        "game_id": game_id,
                        "username": username,
                        "move_number": idx,
                        "uci_move": uci,
                        # "fen": snap.get("fen"),  # current-game JSON may or may not include fen
                        "ts": int(time.time() * 1000),
                    }
                    producer.produce(
                        topic_live_moves,
                        key=game_id,  # key by game_id => ordering per game
                        value=json.dumps(move_payload),
                        callback=delivery_report,
                    )
                    print(f"[MOVE] game_id={game_id} #{idx} {uci}", flush=True)

                # serve callbacks
                producer.poll(0)
                last_moves = moves

            producer.poll(0)
            time.sleep(poll_seconds)

        except requests.RequestException as e:
            print(f"[HTTP_ERROR] {e}", flush=True)
            time.sleep(2)
        except Exception as e:
            print(f"[ERROR] {e}", flush=True)
            time.sleep(2)


def main():
    username = sys.argv[1] if len(sys.argv) > 1 else os.getenv("LICHESS_USERNAME")
    if not username:
        raise SystemExit("Usage: python producer_lichess.py <lichess_username>")

    # config = read_config(os.getenv("KAFKA_CONFIG", "client.properties"))
    config_path = Path(os.getenv("KAFKA_CONFIG", str(PROJECT_ROOT / "client.properties")))
    
    config = read_config(str(config_path))

    print(f"[CONFIG] using client.properties at: {config_path}", flush=True)


    topic_player_profile = os.getenv("TOPIC_PLAYER_PROFILE", "player_profile")
    topic_live_moves = os.getenv("TOPIC_LIVE_MOVES", "live_moves")
    topic_session_events = os.getenv("TOPIC_SESSION_EVENTS", "session_events")

    poll_seconds = float(os.getenv("POLL_SECONDS", "1.0"))
    exit_on_game_end = os.getenv("EXIT_ON_GAME_END", "false").lower() == "true"

    produce_lichess_stream(
        username=username,
        topic_player_profile=topic_player_profile,
        topic_live_moves=topic_live_moves,
        topic_session_events=topic_session_events,
        config=config,
        poll_seconds=poll_seconds,
        exit_on_game_end=exit_on_game_end,
    )


if __name__ == "__main__":
    main()
