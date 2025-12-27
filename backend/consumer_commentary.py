import base64
import json
import os
import re
import time
from dataclasses import dataclass, field
from typing import Any, Dict, Tuple

from confluent_kafka import Consumer, Producer
from google import genai



# ---------------------------
# Config
# ---------------------------

from pathlib import Path
from dotenv import load_dotenv

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
    username: str
    last_commentary_ts: float = 0.0
    last_commentary_move: int = 0
    phase: str = "opening"
    is_first_commentary: bool = True
    last_seen_ts: float = field(default_factory=lambda: time.time())


STORE: Dict[str, GameState] = {}

# ---------------------------
# Heuristics
# ---------------------------

def get_player_color(snap, username):
    if snap["players"]["white"]["user"]["name"] == username:
        return "white"
    if snap["players"]["black"]["user"]["name"] == username:
        return "black"
    return None

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
        print(move_list)
        last_move = move_list[-1]

    if len(move_list) == 0:
        move_player = 'Nobody Played Yet'

    elif len(move_list) % 2 ==0:
        move_player = 'Black'
    else:
        move_player = 'White'

    return last_move, move_player

# ---------------------------
# Prompt + output rules
# ---------------------------

def build_initial_prompt(
    st: GameState,
    snap: dict,
) -> str:
    profile_str = json.dumps(st.profile_json, ensure_ascii=False)
    snap_str = json.dumps(snap, ensure_ascii=False)
    st.is_first_commentary = False
    username_color = get_player_color(snap, st.username)

    return (
        "You are a world-class chess commentator in the style of Judit Polgar.\n\n"
        "This is the FIRST commentary of the game — the live broadcast opening.\n\n"
        f"We are following the player '{st.username}', playing as {username_color}.\n\n"
        "Player profile (long-term identity, habits, psychology):\n"
        f"{profile_str}\n\n"
        "Current game snapshot (may include opponent rating, time control, and move list):\n"
        f"{snap_str}\n\n"
        "Instructions:\n"
        "- Welcome the audience as if they are just tuning in.\n"
        "- Use the snapshot to set the stakes (rating gap, colors, time control, recent form).\n"
        "- If the move list is EMPTY or absent, build anticipation and tension before the first blow.\n"
        "- If the move list EXISTS, briefly frame the opening direction and early intentions without naming theory.\n"
        "- Emphasize the psychological and physical toll of competitive chess.\n\n"
        "Output rules (VERY IMPORTANT):\n"
        "- Respond with EXACTLY ONE spoken sentence.\n"
        "- Sound like live commentary, not analysis or narration.\n"
        "- Be opinionated, confident, and human.\n"
        "- Do NOT explain rules, openings, or teach the audience.\n"
    )


def build_live_prompt(
    st: GameState,
    player_colour: str,
    latest_move: str,
    snap: dict,
) -> str:
    profile_str = json.dumps(st.profile_json, ensure_ascii=False)
    snap_str = json.dumps(snap, ensure_ascii=False)
    username_color = get_player_color(snap, st.username)
    print("LATEST MOVE IN PROMPT BUILDING : ", latest_move)

    return (
        "You are a world-class live chess commentator.\n\n"
        f"We are following the player '{st.username}', playing as {username_color}.\n\n"
        f"Player that just moved is {player_colour}.\n\n"
        "Player profile (long-term identity, habits, psychology, recent form):\n"
        f"{profile_str}\n\n"
        "Current game snapshot (position, opponent rating, time control, opening, move list):\n"
        f"{snap_str}\n\n"
        f"The latest move just played is: {latest_move}\n\n"
        "Your task:\n"
        "- React to the latest move as live commentary.\n"
        "- RANDOMLY choose ONE of the following commentary angles.\n"
        "- Weight your choice toward the first two options most of the time.\n\n"
        "Commentary angle options (choose ONE at random):\n"
        "1) What the latest move does to the position and why it matters (MOST COMMON)\n"
        "2) Why the player likely chose this move right now, based on intent or pressure (MOST COMMON)\n"
        "3) What this move reveals about the player’s psychology, habits, or current form\n"
        "4) A brief historical or stylistic insight related to the opening or structure\n\n"
        "Rules:\n"
        "- Focus primarily on the latest move even if you choose psychology or history.\n"
        "- Do NOT list variations, engine lines, or teach theory.\n"
        "- Sound human, opinionated, and spoken.\n"
        "- Respond with ONE OR TWO sentences MAXIMUM — never more.\n"
        "- This should feel like live broadcast commentary, not analysis notes.\n"
    )


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
            profile = payload.get("profile", {})

            # Ignore our own emitted audio messages to prevent loops (since output is same topic)
            if "audio_base64" in payload:
                continue

            # --- Profile messages ---
            # Accept either explicit event or schema shape (in case producer doesn't include event)
            if event == "player_profile":
                game_id = payload["game_id"]
                profile = profile

                STORE[game_id] = GameState(
                    profile_json=profile,
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

                latest_move, player_colour = calculate_latest_move(snap)
                print(
                    f"[MOVE] game_id={game_id} #{move_number} Latest Move ={latest_move} player colour ={player_colour} ",
                    flush=True,
                )

                # Open for conditions where we want to limit commentary
                # if not decision:
                #     continue

                print("BUILDING PROMPT")

                if st.is_first_commentary:
                    print("CALLING LLM - FIRST COMMENTARY")
                    prompt = build_initial_prompt(st, snap)
                else:
                    print("CALLING LLM")
                    prompt = build_live_prompt(st, player_colour, latest_move, snap)



                # --- LABEL: CALL_LLM ---
                raw_text = call_llm(prompt)

                # --- LABEL: CALL_ELEVENLABS ---
                audio_bytes, audio_fmt = call_elevenlabs_tts(raw_text)

                out = {
                    "event": "commentary_audio",  # helpful in single-topic mode
                    "game_id": game_id,
                    "move_number": move_number,
                    "commentary_text": raw_text,
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
