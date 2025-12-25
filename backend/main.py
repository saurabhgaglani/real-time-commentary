from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from datetime import date, timedelta, datetime
import requests
import json


app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173","http://127.0.0.1:5174"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

BASE_URL = "https://lichess.org"

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
    data = r.json()

    return data


def fetch_rating_history(username: str):
    url = f"{BASE_URL}/api/user/{username}/rating-history"

    r = requests.get(url, headers={"Accept": "application/json"})
    r.raise_for_status()
    data = r.json()

    return data


def fetch_games(username: str, max_games: int = 80, color: str | None = None):
    url = f"{BASE_URL}/api/games/user/{username}"

    params = {
        "max": max_games,
        "moves": "true",
        "opening": "true",
        "accuracy": "true",
        "literate": "true",
        "sort": "dateDesc"
    }

    # Apply color filter if provided
    if color in {"white", "black"}:
        params["color"] = color

    headers = {
        "Accept": "application/x-ndjson"
    }

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

def build_rating_narrative(rating_history):
    print("[ANALYZE] Building rating narrative (corrected)")

    variants_of_interest = {"Rapid", "Blitz", "Bullet"}
    result = {}

    for entry in rating_history:
        name = entry.get("name")
        if name not in variants_of_interest:
            continue

        points = normalize_points(entry.get("points", []))

        weekly = rating_change_over_period(points, 7)
        monthly = rating_change_over_period(points, 30)
        yearly = rating_change_over_period(points, 365)

        result[name.lower()] = {
            "weekly_change": weekly,
            "monthly_change": monthly,
            "yearly_change": yearly,
        }

        print(f"[ANALYZE] {name}: week={weekly}, month={monthly}, year={yearly}")

    return result

def extract_behavioral_profile(username: str, max_games: int = 80):
    white_games = fetch_games(username, max_games=max_games, color="white")
    black_games = fetch_games(username, max_games=max_games, color="black")

    def analyze_games(games, color: str):
        first_moves = {}
        openings = {}
        last_result = None  # <-- added

        for g in games:
            # Capture most recent game result (games are dateDesc)
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
                    "result": result
                }

            moves = g.get("moves", "").split()

            # Correct ply indexing for first move
            if color == "white" and len(moves) >= 1:
                move = moves[0]
            elif color == "black" and len(moves) >= 2:
                move = moves[1]
            else:
                move = None

            if move:
                first_moves[move] = first_moves.get(move, 0) + 1

            opening = g.get("opening")
            if not opening:
                continue

            name = opening.get("name")
            if not name:
                continue

            if name not in openings:
                openings[name] = {"games": 0, "wins": 0}

            openings[name]["games"] += 1

            # Correct win detection
            if g.get("winner") == color:
                openings[name]["wins"] += 1

        top_openings = sorted(
            openings.items(),
            key=lambda x: x[1]["games"],
            reverse=True
        )[:5]

        return {
            "preferred_first_move": (
                max(first_moves, key=first_moves.get)
                if first_moves else "unknown"
            ),
            "top_openings": [
                {
                    "name": name,
                    "games_played": data["games"],
                    "win_rate_pct": round(
                        (data["wins"] / data["games"]) * 100, 2
                    ) if data["games"] else 0.0,
                }
                for name, data in top_openings
            ],
            "last_result": last_result  # <-- returned here
        }

    white_profile = analyze_games(white_games, "white")
    black_profile = analyze_games(black_games, "black")

    # Single global game-length average
    all_lengths = [
        len(g.get("moves", "").split())
        for g in white_games + black_games
        if g.get("moves")
    ]

    avg_length_all = (
        sum(all_lengths) // len(all_lengths)
        if all_lengths else 0
    )

    if avg_length_all < 50:
        style = "sharp"
    elif avg_length_all > 70:
        style = "patient"
    else:
        style = "balanced"

    return {
        "white": white_profile,
        "black": black_profile,
        "average_game_length": avg_length_all,
        "style": style
    }

# ------------------
# Helpers
# ------------------

def normalize_points(points):
    """
    Converts Lichess points to sorted list of (date, rating)
    """
    normalized = []
    for y, m, d, r in points:
        normalized.append((date(y, m + 1, d), r))  # Lichess months are 0-based
    return sorted(normalized, key=lambda x: x[0])

def rating_change_over_period(points, days):
    """
    Computes rating change over last N days
    """
    if not points:
        return None

    today = date.today()
    cutoff = today - timedelta(days=days)

    start_rating = None
    for dt, rating in points:
        if dt <= cutoff:
            start_rating = rating

    end_rating = points[-1][1]

    if start_rating is None:
        return None  # insufficient history

    return end_rating - start_rating


# ------------------
# Analyze endpoint
# ------------------

@app.post("/analyze")
def analyze(payload: dict):
    print("[REQUEST] Analyze payload:", payload)

    username = payload.get("username")
    if not username:
        print("[ERROR] Username missing")
        return {"error": "username required"}

    user_profile = fetch_user_profile(username)
    rating_history = fetch_rating_history(username)

    rating_narrative = build_rating_narrative(rating_history)
    behavior = extract_behavioral_profile(username)

    profile = {
        "identity": {
            "username": username,
            "rapid_rating": user_profile["perfs"].get("rapid", {}).get("rating"),
            "rapid_games": user_profile["perfs"].get("rapid", {}).get("games"),
            "blitz_rating": user_profile["perfs"].get("blitz", {}).get("rating"),
            "blitz_games": user_profile["perfs"].get("blitz", {}).get("games"),
        },
        "rating_narrative": rating_narrative,
        "behavior": behavior
    }

    print("[RESPONSE] Profile ready")
    return {
        "username": username,
        "profile": profile,
        "status": "ready"
    }
