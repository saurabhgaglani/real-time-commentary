from fastapi import FastAPI
import requests
import chess.pgn
from io import StringIO
from fastapi.middleware.cors import CORSMiddleware


app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health():
    return {"status": "ok"}

def fetch_games(username: str, max_games: int = 20):
    url = f"https://lichess.org/api/games/user/{username}"
    params = {
        "max": max_games,
        "perfType": "rapid,blitz,classical"
    }
    headers = {
        "Accept": "application/x-chess-pgn"
    }

    resp = requests.get(url, params=params, headers=headers)
    resp.raise_for_status()
    return resp.text

def extract_profile(pgn_text: str):
    pgn_io = StringIO(pgn_text)

    e4_count = 0
    d4_count = 0
    total_games = 0
    game_lengths = []

    while True:
        game = chess.pgn.read_game(pgn_io)
        if game is None:
            break

        total_games += 1
        board = game.board()
        moves = list(game.mainline_moves())

        if moves:
            first_move = moves[0].uci()
            if first_move.startswith("e2e4"):
                e4_count += 1
            if first_move.startswith("d2d4"):
                d4_count += 1

        game_lengths.append(len(moves))

    style = "unknown"
    if e4_count > d4_count:
        style = "prefers e4 openings"
    elif d4_count > e4_count:
        style = "prefers d4 openings"

    avg_length = sum(game_lengths) // len(game_lengths) if game_lengths else 0

    return {
        "games_analyzed": total_games,
        "opening_preference": style,
        "average_game_length": avg_length
    }

@app.post("/analyze")
def analyze(payload: dict):
    username = payload.get("username")
    if not username:
        return {"error": "username required"}

    pgn_text = fetch_games(username)
    profile = extract_profile(pgn_text)

    return {
        "username": username,
        "profile": profile,
        "status": "ready"
    }
