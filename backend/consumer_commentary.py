import base64
import json
import os
import re
import time
from dataclasses import dataclass, field
from typing import Any, Dict, Optional

from confluent_kafka import Consumer, Producer



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


TOPIC_PLAYER_PROFILE = os.getenv("TOPIC_PLAYER_PROFILE", "player_profile")
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
    profile_summary_text: str
    expected_style: str
    risk_tolerance: str
    last_commentary_ts: float = 0.0
    last_commentary_move: int = 0
    phase: str = "opening"
    last_seen_ts: float = field(default_factory=lambda: time.time())


STORE: Dict[str, GameState] = {}


# ---------------------------
# Profile compression
# ---------------------------

def compress_profile(profile: Dict[str, Any]) -> tuple[str, str, str]:
    openings = profile.get("preferred_openings") or []
    style = str(profile.get("style") or "unknown").strip().lower()
    risk = str(profile.get("risk_tolerance") or "unknown").strip().lower()

    bullets = []
    if openings:
        bullets.append(f"- Usually prefers comfort openings like {', '.join(openings[:3])}.")
    else:
        bullets.append("- Has recognizable comfort patterns early on.")

    if style in {"solid", "defensive"}:
        bullets.append("- Typically plays solid and avoids messy complications.")
    elif style in {"aggressive", "tactical"}:
        bullets.append("- Usually plays aggressively and looks for initiative.")
    else:
        bullets.append("- Style varies but tends to repeat familiar plans.")

    if risk == "low":
        bullets.append("- Low risk tolerance: prefers safety over sharp gambles.")
    elif risk == "high":
        bullets.append("- High risk tolerance: comfortable taking big chances.")
    else:
        bullets.append("- Risk tolerance is mixed depending on position.")

    summary = "Player tendencies:\n" + "\n".join(bullets[:5])
    return summary, style or "unknown", risk or "unknown"


# ---------------------------
# Heuristics
# ---------------------------

def derive_phase(move_number: int) -> str:
    if move_number <= 10:
        return "opening"
    if move_number <= 30:
        return "midgame"
    return "endgame"


def derive_move_character(move_number: int, uci_move: Optional[str]) -> str:
    u = (uci_move or "").lower()
    # simple: early wing pawn push => aggressive
    if move_number <= 8 and len(u) >= 2 and u[0] in {"a", "h"}:
        return "aggressive"
    # early g-pawn push => risky
    if move_number <= 10 and len(u) >= 2 and u[0] == "g":
        return "risky"
    return "solid"


def derive_deviation(expected_style: str, risk_tolerance: str, move_character: str) -> str:
    exp = (expected_style or "unknown").lower()
    risk = (risk_tolerance or "unknown").lower()

    score = 0
    if exp in {"solid", "defensive"} and move_character in {"aggressive", "risky"}:
        score += 2
    if risk == "low" and move_character == "risky":
        score += 2

    if score >= 3:
        return "high"
    if score == 2:
        return "moderate"
    return "low"


def should_comment(st: GameState, move_number: int, phase: str, move_character: str, deviation: str, phase_transition: bool) -> bool:
    now = time.time()
    if (now - st.last_commentary_ts) < COOLDOWN_SECONDS:
        return False
    if (move_number - st.last_commentary_move) < MIN_MOVES_BETWEEN_COMMENTS:
        return False

    if phase_transition:
        return True
    if deviation in {"moderate", "high"}:
        return True
    if move_character in {"risky", "surprising"}:
        return True
    return False


# ---------------------------
# Prompt + output rules
# ---------------------------

_SAN_RE = re.compile(r"\b[KQRBN]?[a-h]?[1-8]?x?[a-h][1-8](=[QRBN])?[+#]?\b")
_UCI_RE = re.compile(r"\b[a-h][1-8][a-h][1-8][qrbn]?\b", re.IGNORECASE)

def build_prompt(st: GameState, phase: str, move_character: str, deviation: str) -> str:
    return (
        "You are a chess commentator.\n\n"
        f"{st.profile_summary_text}\n\n"
        "Current situation:\n"
        f"- Phase: {phase}\n"
        f"- Expected style: {st.expected_style}\n"
        f"- Actual move type: {move_character}\n"
        f"- Deviation level: {deviation}\n\n"
        "React in one spoken sentence. Be opinionated and human.\n"
        "Do not explain chess theory.\n\n"
        "Rules:\n"
        "One sentence only\n"
        "No engine evaluations\n"
        "No move notation\n"
        "No technical language\n"
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
    print("Called the LLM")

    # --- CALL_LLM: START ---
    return "That’s a surprisingly bold choice for someone who usually plays it safe."
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
    # config = read_config(os.getenv("KAFKA_CONFIG", "client.properties"))
    config_path = Path(os.getenv("KAFKA_CONFIG", str(PROJECT_ROOT / "client.properties")))
    config = read_config(str(config_path))

    print(f"[CONFIG] using client.properties at: {config_path}", flush=True)


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
            if event == "player_profile" or ("profile" in payload and "game_id" in payload and "username" in payload):
                game_id = payload["game_id"]
                profile = payload.get("profile", {})
                summary, style, risk = compress_profile(profile)

                STORE[game_id] = GameState(
                    profile_summary_text=summary,
                    expected_style=style,
                    risk_tolerance=risk,
                )
                print(f"[PROFILE] cached game_id={game_id}", flush=True)
                continue

            # --- Session start/end (optional logging) ---
            if event in {"session_start", "session_end"}:
                print(f"[SESSION] {event} game_id={payload.get('game_id')} user={payload.get('username')}", flush=True)
                continue

            # --- Live move messages ---
            if event == "live_move" or ("uci_move" in payload and "move_number" in payload and "game_id" in payload):
                game_id = payload["game_id"]
                move_number = int(payload["move_number"])
                uci_move = payload.get("uci_move")

                st = STORE.get(game_id)
                if not st:
                    print(f"[NO_PROFILE] game_id={game_id} move={move_number}", flush=True)
                    continue

                prev_phase = st.phase
                phase = derive_phase(move_number)
                st.phase = phase
                phase_transition = (prev_phase != phase)

                move_character = derive_move_character(move_number, uci_move)
                deviation = derive_deviation(st.expected_style, st.risk_tolerance, move_character)

                decision = should_comment(st, move_number, phase, move_character, deviation, phase_transition)
                print(
                    f"[MOVE] game_id={game_id} #{move_number} type={move_character} dev={deviation} speak={decision}",
                    flush=True,
                )

                if not decision:
                    continue

                prompt = build_prompt(st, phase, move_character, deviation)

                # --- LABEL: CALL_LLM ---
                raw_text = call_llm(prompt)
                commentary_text = sanitize_text(raw_text)

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

            # Unknown message type on the shared topic
            # (Keep silent or log once if you prefer.)
            # print(f"[SKIP] unknown payload keys={list(payload.keys())}", flush=True)

    except KeyboardInterrupt:
        print("\n[SHUTDOWN]", flush=True)
    finally:
        consumer.close()


# def main():
#     config = read_config(os.getenv("KAFKA_CONFIG", "client.properties"))

#     # Consumer config
#     consumer_conf = dict(config)
#     consumer_conf["group.id"] = GROUP_ID
#     consumer_conf["auto.offset.reset"] = AUTO_OFFSET_RESET

#     consumer = Consumer(consumer_conf)
#     consumer.subscribe([TOPIC_PLAYER_PROFILE, TOPIC_LIVE_MOVES])

#     # Producer for output audio events
#     producer = Producer(config)

#     print(f"[BOOT] consuming: {TOPIC_PLAYER_PROFILE}, {TOPIC_LIVE_MOVES} | producing: {TOPIC_OUT_AUDIO}", flush=True)

#     try:
#         while True:
#             msg = consumer.poll(1.0)
#             if msg is None:
#                 continue
#             if msg.error():
#                 print(f"[KAFKA_ERROR] {msg.error()}", flush=True)
#                 continue

#             topic = msg.topic()
#             payload = json.loads(msg.value().decode("utf-8"))

#             if topic == TOPIC_PLAYER_PROFILE:
#                 game_id = payload["game_id"]
#                 profile = payload.get("profile", {})
#                 summary, style, risk = compress_profile(profile)

#                 STORE[game_id] = GameState(
#                     profile_summary_text=summary,
#                     expected_style=style,
#                     risk_tolerance=risk,
#                 )
#                 print(f"[PROFILE] cached game_id={game_id}", flush=True)
#                 continue

#             if topic == TOPIC_LIVE_MOVES:
#                 game_id = payload["game_id"]
#                 move_number = int(payload["move_number"])
#                 uci_move = payload.get("uci_move")

#                 st = STORE.get(game_id)
#                 if not st:
#                     print(f"[NO_PROFILE] game_id={game_id} move={move_number}", flush=True)
#                     continue

#                 prev_phase = st.phase
#                 phase = derive_phase(move_number)
#                 st.phase = phase
#                 phase_transition = (prev_phase != phase)

#                 move_character = derive_move_character(move_number, uci_move)
#                 deviation = derive_deviation(st.expected_style, st.risk_tolerance, move_character)

#                 decision = should_comment(st, move_number, phase, move_character, deviation, phase_transition)
#                 print(f"[MOVE] game_id={game_id} #{move_number} type={move_character} dev={deviation} speak={decision}", flush=True)

#                 if not decision:
#                     continue

#                 prompt = build_prompt(st, phase, move_character, deviation)

#                 # --- LABEL: CALL_LLM ---
#                 raw_text = call_llm(prompt)
#                 commentary_text = sanitize_text(raw_text)

#                 # --- LABEL: CALL_ELEVENLABS ---
#                 audio_bytes, audio_fmt = call_elevenlabs_tts(commentary_text)

#                 out = {
#                     "game_id": game_id,
#                     "move_number": move_number,
#                     "commentary_text": commentary_text,
#                     "audio_format": audio_fmt,
#                     "audio_base64": base64.b64encode(audio_bytes).decode("utf-8"),
#                     "created_at_ms": int(time.time() * 1000),
#                 }

#                 # --- LABEL: PRODUCE_AUDIO ---
#                 producer.produce(
#                     TOPIC_OUT_AUDIO,
#                     key=game_id,
#                     value=json.dumps(out).encode("utf-8"),
#                 )
#                 producer.flush()

#                 st.last_commentary_ts = time.time()
#                 st.last_commentary_move = move_number

#                 print(f"[AUDIO] emitted game_id={game_id} move={move_number}", flush=True)

#     except KeyboardInterrupt:
#         print("\n[SHUTDOWN]", flush=True)
#     finally:
#         consumer.close()


if __name__ == "__main__":
    main()
