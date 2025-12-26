from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from datetime import date, timedelta, datetime
from pathlib import Path
import requests
import json
import os

from confluent_kafka import Producer

####
import os
from pathlib import Path

from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(PROJECT_ROOT / ".env")

print("=== MAIN.PY ENV DEBUG ===", flush=True)
print("PID =", os.getpid(), flush=True)
print("CWD =", Path.cwd(), flush=True)

print("TOPIC_PROFILE_IN =", os.getenv("TOPIC_PROFILE_IN"), flush=True)
print("KAFKA_CONFIG =", os.getenv("KAFKA_CONFIG"), flush=True)
print("KAFKA_BOOTSTRAP_SERVERS =", os.getenv("bootstrap.servers"), flush=True)
print("=========================", flush=True)
####

# ------------------
# FastAPI setup
# ------------------

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

BASE_URL = "https://lichess.org"

# ------------------
# Kafka setup
# ------------------

PROJECT_ROOT = Path(__file__).resolve().parent.parent
KAFKA_CONFIG_PATH = Path(os.getenv("KAFKA_CONFIG", str(PROJECT_ROOT / "client.properties")))
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

def publish_profile_to_kafka(username: str, profile: dict, producer):

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
    print(f"[KAFKA] Profile published for {username}")


# ------------------
# Health check
# ------------------

@app.get("/health")
def health():
    return {"status": "ok"}

# ------------------
# Lichess fetchers
# ------------------

def fetch_user_profile(username: str):
    url = f"{BASE_URL}/api/user/{username}"
    r = requests.get(url, headers={"Accept": "application/json"})
    r.raise_for_status()
    return r.json()


def fetch_rating_history(username: str):
    url = f"{BASE_URL}/api/user/{username}/rating-history"
    r = requests.get(url, headers={"Accept": "application/json"})
    r.raise_for_status()
    return r.json()


def fetch_games(username: str, max_games: int = 30, color: str | None = None):
    url = f"{BASE_URL}/api/games/user/{username}"

    params = {
        "max": max_games,
        "moves": "true",
        "opening": "true",
        "accuracy": "true",
        "literate": "true",
        "sort": "dateDesc",
    }

    if color in {"white", "black"}:
        params["color"] = color

    headers = {"Accept": "application/x-ndjson"}

    games = []
    with requests.get(url, params=params, headers=headers, stream=True) as r:
        r.raise_for_status()
        for line in r.iter_lines():
            if line:
                games.append(json.loads(line.decode("utf-8")))

    return games


# ------------------
# Profile builders
# ------------------

def normalize_points(points):
    normalized = []
    for y, m, d, r in points:
        normalized.append((date(y, m + 1, d), r))
    return sorted(normalized, key=lambda x: x[0])


def rating_change_over_period(points, days):
    if not points:
        return None

    today = date.today()
    cutoff = today - timedelta(days=days)

    start_rating = None
    for dt, rating in points:
        if dt <= cutoff:
            start_rating = rating

    if start_rating is None:
        return None

    return points[-1][1] - start_rating


def build_rating_narrative(rating_history):
    variants = {"Rapid", "Blitz", "Bullet"}
    result = {}

    for entry in rating_history:
        name = entry.get("name")
        if name not in variants:
            continue

        points = normalize_points(entry.get("points", []))

        result[name.lower()] = {
            "weekly_change": rating_change_over_period(points, 7),
            "monthly_change": rating_change_over_period(points, 30),
            "yearly_change": rating_change_over_period(points, 365),
        }

    return result


def extract_behavioral_profile(username: str, max_games: int = 50):
    white_games = fetch_games(username, max_games, "white")
    black_games = fetch_games(username, max_games, "black")

    def analyze(games, color):
        first_moves = {}
        openings = {}
        last_result = None

        for g in games:
            if last_result is None:
                winner = g.get("winner")
                if winner == color:
                    result = "win"
                elif winner is None:
                    result = "draw"
                else:
                    result = "loss"
                last_result = {
                    "time_control": g.get("speed"),
                    "result": result,
                }

            moves = g.get("moves", "").split()
            move = (
                moves[0] if color == "white" and len(moves) >= 1
                else moves[1] if color == "black" and len(moves) >= 2
                else None
            )

            if move:
                first_moves[move] = first_moves.get(move, 0) + 1

            opening = g.get("opening", {}).get("name")
            if not opening:
                continue

            if opening not in openings:
                openings[opening] = {"games": 0, "wins": 0}

            openings[opening]["games"] += 1
            if g.get("winner") == color:
                openings[opening]["wins"] += 1

        top_openings = sorted(
            openings.items(),
            key=lambda x: x[1]["games"],
            reverse=True,
        )[:5]

        return {
            "preferred_first_move": max(first_moves, key=first_moves.get)
            if first_moves else "unknown",
            "top_openings": [
                {
                    "name": name,
                    "games_played": d["games"],
                    "win_rate_pct": round(
                        (d["wins"] / d["games"]) * 100, 2
                    ) if d["games"] else 0.0,
                }
                for name, d in top_openings
            ],
            "last_result": last_result,
        }

    white = analyze(white_games, "white")
    black = analyze(black_games, "black")

    all_lengths = [
        len(g.get("moves", "").split())
        for g in white_games + black_games
        if g.get("moves")
    ]

    avg_len = sum(all_lengths) // len(all_lengths) if all_lengths else 0

    style = (
        "sharp" if avg_len < 50
        else "patient" if avg_len > 70
        else "balanced"
    )

    return {
        "white": white,
        "black": black,
        "average_game_length": avg_len,
        "style": style,
    }


# ------------------
# Analyze endpoint
# ------------------

@app.post("/analyze")
def analyze(payload: dict):
    print("[REQUEST] Analyze payload:", payload)
    kafka_config = load_kafka_config(KAFKA_CONFIG_PATH)
    producer = Producer(kafka_config)

    username = payload.get("username")
    if not username:
        return {"error": "username required"}

    user_profile = fetch_user_profile(username)
    rating_history = fetch_rating_history(username)

    profile = {
        "identity": {
            "username": username,
            "rapid_rating": user_profile["perfs"].get("rapid", {}).get("rating"),
            "rapid_games": user_profile["perfs"].get("rapid", {}).get("games"),
            "blitz_rating": user_profile["perfs"].get("blitz", {}).get("rating"),
            "blitz_games": user_profile["perfs"].get("blitz", {}).get("games"),
        },
        "rating_narrative": build_rating_narrative(rating_history),
        "behavior": extract_behavioral_profile(username),
    }

    publish_profile_to_kafka(username, profile, producer)

    return {
        "username": username,
        "profile": profile,
        "status": "ready",
    }
