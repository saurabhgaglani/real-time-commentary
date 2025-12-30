import base64
import json
import os
import re
import time
from dataclasses import dataclass, field
from typing import Any, Dict, Tuple

from confluent_kafka import Consumer, Producer
from google import genai

from elevenlabs.client import ElevenLabs
from elevenlabs.play import play, save
import time



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
elevenlabs_api_key = os.getenv("ELEVENLABS_API_KEY")

TOPIC_PLAYER_PROFILE = os.getenv("TOPIC_PROFILE_IN", "player_profile_input")
TOPIC_LIVE_MOVES = os.getenv("TOPIC_LIVE_MOVES", "live_moves")
TOPIC_OUT_AUDIO = os.getenv("TOPIC_OUT_AUDIO", "commentary_audio")

GROUP_ID = os.getenv("KAFKA_GROUP_ID", "commentary-consumer-group-1")
AUTO_OFFSET_RESET = os.getenv("AUTO_OFFSET_RESET", "latest")

COOLDOWN_SECONDS = float(os.getenv("COOLDOWN_SECONDS", "2"))
MIN_MOVES_BETWEEN_COMMENTS = int(os.getenv("MIN_MOVES_BETWEEN_COMMENTS", "3"))
AUDIO_PATH = os.path.join(PROJECT_ROOT, 'audio')


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
        "You are a world-class live chess commentator delivering the broadcast opening.\n\n"
        f"We are following '{st.username}' as {username_color}.\n\n"
        "Use this player profile and game snapshot:\n"
        f"PROFILE:\n{profile_str}\n\n"
        f"SNAPSHOT:\n{snap_str}\n\n"
        "Write ONE single spoken sentence that sounds like a human on live TV.\n"
        "Make it feel mid-flow and confident.\n"
        "Anchor the sentence on the player’s recent form from the profile: last week, month, year, and any White-vs-Black trend.\n"
        "Use the snapshot only to set stakes (time control/ratings/colors).\n"
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
        "You are providing live chess commentary in a broadcast already in progress.\n\n"
        f"We are following the player '{st.username}', playing as {username_color}.\n\n"
        f"Player that just moved is {player_colour}.\n\n"
        "Player profile (long-term identity, habits, psychology, recent form):\n"
        f"{profile_str}\n\n"
        "Current game snapshot (position, opponent rating, time control, opening, move list):\n"
        f"{snap_str}\n\n"
        f"The latest move just played is: {latest_move}\n\n"
        "ABSOLUTE OUTPUT CONSTRAINT (MANDATORY):\n"
        "- Output MUST be 20 words or fewer.\n"
        "- Output MUST be exactly 1 or 2 short sentences.\n"
        "- If output exceeds 20 words, it is INVALID and WRONG.\n\n"
        "LANGUAGE CONSTRAINT:\n"
        "- Sentences must be short, spoken, and natural.\n"
        "- No long clauses. No stacked ideas.\n\n"
        "BEFORE OUTPUT:\n"
        "- Silently count words.\n"
        "- Silently count sentences.\n"
        "- Reduce until BOTH limits are satisfied.\n\n"
        "Your task:\n"
        "- React to the latest move as live commentary.\n"
        "- RANDOMLY choose ONE commentary angle.\n"
        "- Bias heavily toward the first two options.\n\n"
        "Commentary angle options (choose ONE):\n"
        "1) What the move does to the position and why it matters(from snapshot given above) (MOST COMMON)\n"
        "3) Why this players recent form might factor into the move he has played(from player profile given above)\n"
        "4) A brief stylistic or historical insight(from player profile given above)\n\n"
        "STRICT RULES:\n"
        "- No introductions or acknowledgements.\n"
        "- No restarts or recap language.\n"
        "- No engine evaluations or theory.\n"
        "- Mid-broadcast tone only.\n"
        "- Confident, human, flowing speech.\n"
        "- Under NO circumstances output more than 20 words.\n"
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

def get_filename():
    """
    Returns timestamp as text for tts filename
    Sample return text: 'Sat_Dec_27_002210_2025'
    """

    current_time = time.asctime()
    
    return current_time.replace(' ', '_').replace(':', '')


def call_elevenlabs_tts(text: str, temp_move_number: int):
    """
    LABEL: CALL_ELEVENLABS
    Implement ElevenLabs TTS here.
    Return (audio_bytes, audio_format).
    """

    voice_id = ""
   
    if temp_move_number %2==0:
        voice_id = "Cvv0EXhC1Zv7b4a2QfWl" # Monika - Sports Commentator
    else:
        voice_id = "PdJQAOWyIMAQwD7gQcSc" # Viraj - Sports Commentor
    

    elevenlabs = ElevenLabs(
    api_key = elevenlabs_api_key,
    )

    audio = elevenlabs.text_to_dialogue.convert(
        inputs=[
            {
                "text": text,
                "voice_id": voice_id, 
            }
        ]
    )

    file_name = get_filename()

    save(audio, os.path.join(AUDIO_PATH, file_name + ".mp3"))
    
    return f"/audio/{file_name}.mp3"
    


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

                # Check if we already commented on this move
                if st.last_commentary_move >= move_number:
                    print(f"[SKIP] Already commented on move {move_number} (last: {st.last_commentary_move})", flush=True)
                    continue

                # Add cooldown to prevent spam
                current_time = time.time()
                if current_time - st.last_commentary_ts < COOLDOWN_SECONDS:
                    print(f"[COOLDOWN] Skipping move {move_number} - too soon after last commentary", flush=True)
                    continue

                print("BUILDING PROMPT")

                # Properly handle first commentary flag
                if st.is_first_commentary:
                    print("CALLING LLM - FIRST COMMENTARY")
                    prompt = build_initial_prompt(st, snap)
                    st.is_first_commentary = False  # Reset flag after first use
                else:
                    print("CALLING LLM")
                    prompt = build_live_prompt(st, player_colour, latest_move, snap)

                # --- LABEL: CALL_LLM ---
                raw_text = call_llm(prompt)
                
                #switching commentators
                temp_move_number = int(move_number)

                # --- LABEL: CALL_ELEVENLABS ---
                tts_url = call_elevenlabs_tts(raw_text, temp_move_number)
                out = {
                    "event": "commentary_audio",
                    "game_id": game_id,
                    "move_number": move_number,
                    "latest_move": latest_move,
                    "commentary_text": raw_text,
                    "audio_url": tts_url,  
                    "created_at_ms": int(time.time() * 1000),
                }

                # --- LABEL: PRODUCE_AUDIO ---
                producer.produce(
                    TOPIC_OUT_AUDIO,
                    key=game_id,
                    value=json.dumps(out).encode("utf-8"),
                )
                producer.flush()

                # CRITICAL FIX: Update state AFTER successful commentary
                st.last_commentary_ts = current_time
                st.last_commentary_move = move_number

                print(f"[AUDIO] emitted game_id={game_id} move={move_number}", flush=True)
                continue


    except KeyboardInterrupt:
        print("\n[SHUTDOWN]", flush=True)
    finally:
        consumer.close()



if __name__ == "__main__":
    main()
