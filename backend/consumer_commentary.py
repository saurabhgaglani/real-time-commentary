import base64
import json
import os
import re
import time
from dataclasses import dataclass, field
from typing import Any, Dict

from confluent_kafka import Consumer, Producer
from google import genai



# ---------------------------
# Config
# ---------------------------

from pathlib import Path
from dotenv import load_dotenv

# Project structure:
# real-time-commentary/
# ├── client.properties
# └── backend/
#     └── producer_lichess.py

PROJECT_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(PROJECT_ROOT / ".env")  # load .env explicitly

def read_config(path: str = "client.properties") -> dict:
    config = {}
    with open(path) as fh:
        for line in fh:
            line = line.strip()
            if line and not line.startswith("#"):
                k, v = line.split("=", 1)
                config[k.strip()] = v.strip()
    return config

client = genai.Client(api_key=os.getenv("YOUR_API_KEY"))

TOPIC_PLAYER_PROFILE = os.getenv("TOPIC_PROFILE_IN", "player_profile_input")
TOPIC_LIVE_MOVES = os.getenv("TOPIC_LIVE_MOVES", "live_moves")
TOPIC_OUT_AUDIO = os.getenv("TOPIC_OUT_AUDIO", "commentary_audio")

GROUP_ID = os.getenv("KAFKA_GROUP_ID", "commentary-consumer-group-1")
AUTO_OFFSET_RESET = os.getenv("AUTO_OFFSET_RESET", "latest")

COOLDOWN_SECONDS = float(os.getenv("COOLDOWN_SECONDS", "15"))
MIN_MOVES_BETWEEN_COMMENTS = int(os.getenv("MIN_MOVES_BETWEEN_COMMENTS", "3"))




# ---------------------------
# In-memory state
# ---------------------------

@dataclass
class GameState:
    profile_json: dict
    expected_style: str
    username: str
    last_commentary_ts: float = 0.0
    last_commentary_move: int = 0
    phase: str = "opening"
    last_seen_ts: float = field(default_factory=lambda: time.time())


STORE: Dict[str, GameState] = {}


# ---------------------------
# Profile compression
# ---------------------------



def compress_profile(profile: Dict[str, Any]):
    """
        Returns Style and Profile (JSON right now. )
        Risk is unknown since not rxd in the earlier json.
    """
    style = profile.get("behavior", {}).get("style", 'Unknown Style')
    return style, profile



# ---------------------------
# Heuristics
# ---------------------------



def calculate_latest_move(snap):
    """
    Calculates the last move and player who played.
    Input: snap
    Ret: last_move : str, move_player : str
    
    """
    last_move = 'Empty'
    move_list = snap.get('moves', [])

    if isinstance(move_list, str):
        move_list = move_list.split()

    if len(move_list) > 0:
        last_move = move_list[-1]

    if len(move_list) == '0':
        move_player = 'Nobody Played Yet'

    elif len(move_list) % 2 ==0:
        move_player = 'Black'
    else:
        move_player = 'White'

    return last_move, move_player

# ---------------------------
# Prompt + output rules
# ---------------------------

_SAN_RE = re.compile(r"\b[KQRBN]?[a-h]?[1-8]?x?[a-h][1-8](=[QRBN])?[+#]?\b")
_UCI_RE = re.compile(r"\b[a-h][1-8][a-h][1-8][qrbn]?\b", re.IGNORECASE)

def build_prompt(st: GameState, player_colour: str, move_character: str, snap: dict) -> str:
    profile_str = json.dumps(st.profile_json, ensure_ascii=False)
    snap_str = json.dumps(snap, ensure_ascii=False)

    return (
        f"You are a chess commentator like Judit Polgar. Here is the profile JSON for the player we are tracking with the username {st.username}. He is playing as {player_colour}\n\n"
        f"{profile_str}\n\n"
        "Current situation:\n"
        f"- The latest move played is : {move_character}\n"
        f"- Complete Move details in JSON : {snap_str}\n\n"
        "(if absent, pregame). Treat the JSON as the player’s long-term identity (username, habits, style, psychology). Do not let new audiences feel left out make them feel how brutal and taxing chess is. Derive patterns of users play using openings and game lengths and how theyve been playing recently. Talk about whether they are coming off a win or loss with black and white. Build tension up if pregame."
        "React in one spoken sentence. Be opinionated and human.\n"
    )


def sanitize_text(text: str) -> str:
    t = (text or "").strip()

    # force one sentence
    m = re.search(r"[.!?]", t)
    if m:
        t = t[: m.end()].strip()

    # remove chess notation leakage
    t = _SAN_RE.sub("", t)
    t = _UCI_RE.sub("", t)

    t = re.sub(r"\s+", " ", t).strip()
    return t or "That’s an unexpected choice for this player."


# ---------------------------
# External calls (YOU fill)
# ---------------------------

def call_llm(prompt: str) -> str:
    """
    LABEL: CALL_LLM
    Implement sync call to your LLM here (or wrap async elsewhere).
    Return ONE sentence (we sanitize anyway).
    """
    response = client.models.generate_content(
    model="gemma-3-27b-it",
    contents=prompt
    )
    print("LLM Response : ", response.text)
    # --- CALL_LLM: START ---
    return response.text
    # --- CALL_LLM: END ---


def call_elevenlabs_tts(text: str) -> tuple[bytes, str]:
    """
    LABEL: CALL_ELEVENLABS
    Implement ElevenLabs TTS here.
    Return (audio_bytes, audio_format).
    """
    print("TTS just worked")
    # --- CALL_ELEVENLABS: START ---
    return b"FAKEAUDIOBYTES", "mp3"
    # --- CALL_ELEVENLABS: END ---


# ---------------------------
# Kafka loop
# ---------------------------

def main():
    
    config_path = Path(os.getenv("KAFKA_CONFIG", str(PROJECT_ROOT / "client.properties")))
    config = read_config(str(config_path))


    # Consumer config
    consumer_conf = dict(config)
    consumer_conf["group.id"] = GROUP_ID
    consumer_conf["auto.offset.reset"] = AUTO_OFFSET_RESET

    consumer = Consumer(consumer_conf)

    # OPTION A: single topic mode (you mapped all env topics to chess_stream)
    # Subscribe to the unique set to avoid duplicates if they are the same string.
    topics = sorted({TOPIC_PLAYER_PROFILE, TOPIC_LIVE_MOVES})
    consumer.subscribe(topics)

    # Producer for output audio events (in Option A this is also chess_stream)
    producer = Producer(config)

    print(f"[BOOT] consuming: {', '.join(topics)} | producing: {TOPIC_OUT_AUDIO}", flush=True)

    try:
        while True:
            msg = consumer.poll(1.0)
            if msg is None:
                continue
            if msg.error():
                print(f"[KAFKA_ERROR] {msg.error()}", flush=True)
                continue

            payload = json.loads(msg.value().decode("utf-8"))
            event = payload.get("event")  # Option A routing key

            # Ignore our own emitted audio messages to prevent loops (since output is same topic)
            if "audio_base64" in payload:
                continue

            # --- Profile messages ---
            # Accept either explicit event or schema shape (in case producer doesn't include event)
            if event == "player_profile":
                game_id = payload["game_id"]
                profile = payload.get("profile", {})
                style, summary = compress_profile(profile) 

                STORE[game_id] = GameState(
                    profile_json=summary,
                    expected_style=style,
                    username= profile.get("identity", {}).get('username', 'Unknown User')

                )
                print(f"[PROFILE] cached game_id={game_id}", flush=True)
                continue

            # --- Session start/end (optional logging) ---
            if event in {"session_start", "session_end"}:
                print(f"[SESSION] {event} game_id={payload.get('game_id')} user={payload.get('username')}", flush=True)
                continue

            # --- Live move messages ---
            if event == "move":
                game_id = payload["game_id"]
                move_number = int(payload["move_number"])
                uci_move = payload.get("uci_move")
                snap = payload.get("snap")

                st = STORE.get(game_id)
                if not st:
                    print(f"[NO_PROFILE] game_id={game_id} move={move_number}", flush=True)
                    continue

                move_character, player_colour = calculate_latest_move(snap)
                print(
                    f"[MOVE] game_id={game_id} #{move_number} Latest Move ={move_character} player colour ={player_colour} ",
                    flush=True,
                )

                # Open for conditions where we want to limit commentary
                # if not decision:
                #     continue

                print("BUILDING PROMPT")

                prompt = build_prompt(st, player_colour, move_character, snap)

                print("CALLING LLM")

                # --- LABEL: CALL_LLM ---
                raw_text = call_llm(prompt)
                print("RAW RESPONSE : ", raw_text)

                commentary_text = sanitize_text(raw_text)
                print("Sanitized Commentary : ", commentary_text)

                # --- LABEL: CALL_ELEVENLABS ---
                audio_bytes, audio_fmt = call_elevenlabs_tts(commentary_text)

                out = {
                    "event": "commentary_audio",  # helpful in single-topic mode
                    "game_id": game_id,
                    "move_number": move_number,
                    "commentary_text": commentary_text,
                    "audio_format": audio_fmt,
                    "audio_base64": base64.b64encode(audio_bytes).decode("utf-8"),
                    "created_at_ms": int(time.time() * 1000),
                }

                # --- LABEL: PRODUCE_AUDIO ---
                producer.produce(
                    TOPIC_OUT_AUDIO,
                    key=game_id,
                    value=json.dumps(out).encode("utf-8"),
                )
                producer.flush()

                st.last_commentary_ts = time.time()
                st.last_commentary_move = move_number

                print(f"[AUDIO] emitted game_id={game_id} move={move_number}", flush=True)
                continue


    except KeyboardInterrupt:
        print("\n[SHUTDOWN]", flush=True)
    finally:
        consumer.close()



if __name__ == "__main__":
    main()
