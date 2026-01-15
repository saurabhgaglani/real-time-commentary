from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from datetime import date, timedelta, datetime
from pathlib import Path
import requests
import json
import os
import logging
import asyncio

from confluent_kafka import Producer
from backend.websocket_manager import ConnectionManager, KafkaWebSocketBridge

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

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files for audio
audio_dir = PROJECT_ROOT / "audio"
audio_dir.mkdir(exist_ok=True)
app.mount("/audio", StaticFiles(directory=str(audio_dir)), name="audio")

# Initialize WebSocket connection manager
connection_manager = ConnectionManager()

# Initialize Kafka-WebSocket bridge (will be started on app startup)
kafka_bridge = None

BASE_URL = "https://lichess.org"

# ------------------
# Kafka setup
# ------------------

PROJECT_ROOT = Path(__file__).resolve().parent.parent
KAFKA_CONFIG_PATH = Path(os.getenv("KAFKA_CONFIG", str(PROJECT_ROOT / "client.properties")))
PROFILE_TOPIC = os.getenv("TOPIC_PROFILE_IN", "player_profile_input")
COMMENTARY_AUDIO_TOPIC = os.getenv("TOPIC_COMMENTARY_AUDIO", "commentary_audio")


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
# Application lifecycle events
# ------------------

@app.on_event("startup")
async def startup_event():
    """Initialize services on application startup."""
    global kafka_bridge
    
    logging.info("Starting application...")
    logging.info(f"Kafka config path: {KAFKA_CONFIG_PATH}")
    logging.info(f"Commentary audio topic: {COMMENTARY_AUDIO_TOPIC}")
    
    # Initialize and start Kafka-WebSocket bridge
    try:
        kafka_bridge = KafkaWebSocketBridge(
            connection_manager=connection_manager,
            kafka_config_path=KAFKA_CONFIG_PATH,
            topic=COMMENTARY_AUDIO_TOPIC
        )
        
        # Start consuming in background task
        asyncio.create_task(kafka_bridge.start_consuming())
        logging.info("Kafka-WebSocket bridge started successfully")
        
    except Exception as e:
        logging.error(f"Failed to start Kafka-WebSocket bridge: {e}", exc_info=True)


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup services on application shutdown."""
    global kafka_bridge
    
    logging.info("Shutting down application...")
    
    # Stop Kafka consumer gracefully
    if kafka_bridge:
        try:
            await kafka_bridge.stop()
            logging.info("Kafka-WebSocket bridge stopped successfully")
        except Exception as e:
            logging.error(f"Error stopping Kafka-WebSocket bridge: {e}", exc_info=True)


# ------------------
# Health check
# ------------------

@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/api/audio-files")
def list_audio_files():
    """List all audio files in the audio directory."""
    try:
        audio_files = []
        for file in audio_dir.glob("*.mp3"):
            audio_files.append({
                "name": file.name,
                "url": f"/audio/{file.name}"
            })
        return {"files": audio_files, "count": len(audio_files)}
    except Exception as e:
        logging.error(f"Error listing audio files: {e}")
        return {"error": str(e), "files": [], "count": 0}


@app.get("/test-audio")
async def test_audio_page():
    """Serve a test page for audio playback."""
    from fastapi.responses import HTMLResponse
    
    html_content = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Audio Playback Test</title>
    <style>
        body {
            font-family: Arial, sans-serif;
            max-width: 800px;
            margin: 50px auto;
            padding: 20px;
            background: #f5f5f5;
        }
        .container {
            background: white;
            padding: 30px;
            border-radius: 10px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }
        h1 {
            color: #333;
            margin-bottom: 20px;
        }
        .status {
            padding: 10px;
            margin: 10px 0;
            border-radius: 5px;
            font-weight: bold;
        }
        .status.loading {
            background: #fff3cd;
            color: #856404;
        }
        .status.success {
            background: #d4edda;
            color: #155724;
        }
        .status.error {
            background: #f8d7da;
            color: #721c24;
        }
        .audio-list {
            margin: 20px 0;
        }
        .audio-item {
            padding: 15px;
            margin: 10px 0;
            background: #f8f9fa;
            border-radius: 5px;
            border-left: 4px solid #007bff;
        }
        .audio-item.playing {
            background: #e7f3ff;
            border-left-color: #28a745;
        }
        .audio-item.played {
            opacity: 0.6;
        }
        button {
            background: #007bff;
            color: white;
            border: none;
            padding: 12px 24px;
            border-radius: 5px;
            cursor: pointer;
            font-size: 16px;
            margin: 5px;
        }
        button:hover {
            background: #0056b3;
        }
        button:disabled {
            background: #6c757d;
            cursor: not-allowed;
        }
        .controls {
            margin: 20px 0;
        }
        .queue-info {
            padding: 10px;
            background: #e9ecef;
            border-radius: 5px;
            margin: 10px 0;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>🎵 Audio Playback Test</h1>
        
        <div id="status" class="status loading">Loading audio files...</div>
        
        <div class="controls">
            <button id="playBtn" onclick="startPlayback()" disabled>▶️ Play All</button>
            <button id="stopBtn" onclick="stopPlayback()" disabled>⏹️ Stop</button>
            <button onclick="loadAudioFiles()">🔄 Refresh List</button>
        </div>
        
        <div class="queue-info">
            <strong>Queue:</strong> <span id="queueInfo">-</span>
        </div>
        
        <div id="audioList" class="audio-list"></div>
    </div>

    <script>
        let audioFiles = [];
        let currentIndex = 0;
        let isPlaying = false;
        let currentAudio = null;

        async function loadAudioFiles() {
            const statusEl = document.getElementById('status');
            const audioListEl = document.getElementById('audioList');
            
            statusEl.className = 'status loading';
            statusEl.textContent = 'Loading audio files...';
            
            try {
                const response = await fetch('/api/audio-files');
                const data = await response.json();
                
                if (data.error) {
                    throw new Error(data.error);
                }
                
                audioFiles = data.files.map(f => ({
                    name: f.name,
                    url: f.url,
                    played: false
                }));
                
                if (audioFiles.length === 0) {
                    statusEl.className = 'status error';
                    statusEl.textContent = '❌ No audio files found in audio/ folder';
                    audioListEl.innerHTML = '<p>Please generate some audio files first by running consumer_commentary.py</p>';
                    return;
                }
                
                statusEl.className = 'status success';
                statusEl.textContent = `✅ Found ${audioFiles.length} audio file(s)`;
                
                displayAudioFiles();
                document.getElementById('playBtn').disabled = false;
                updateQueueInfo();
                
            } catch (error) {
                statusEl.className = 'status error';
                statusEl.textContent = `❌ Error: ${error.message}`;
                console.error('Error loading audio files:', error);
            }
        }
        
        function displayAudioFiles() {
            const audioListEl = document.getElementById('audioList');
            audioListEl.innerHTML = '<h3>Audio Files:</h3>';
            
            audioFiles.forEach((file, index) => {
                const div = document.createElement('div');
                div.className = 'audio-item';
                div.id = `audio-${index}`;
                div.innerHTML = `
                    <strong>${index + 1}.</strong> ${file.name}
                    <span id="status-${index}"></span>
                `;
                audioListEl.appendChild(div);
            });
        }
        
        function updateQueueInfo() {
            const remaining = audioFiles.length - currentIndex;
            document.getElementById('queueInfo').textContent = `${remaining} file(s) remaining`;
        }
        
        async function startPlayback() {
            if (isPlaying) return;
            
            isPlaying = true;
            currentIndex = 0;
            audioFiles.forEach(f => f.played = false);
            
            document.getElementById('playBtn').disabled = true;
            document.getElementById('stopBtn').disabled = false;
            
            playNext();
        }
        
        function playNext() {
            if (!isPlaying || currentIndex >= audioFiles.length) {
                stopPlayback();
                return;
            }
            
            const file = audioFiles[currentIndex];
            const itemEl = document.getElementById(`audio-${currentIndex}`);
            const statusEl = document.getElementById(`status-${currentIndex}`);
            
            itemEl.className = 'audio-item playing';
            statusEl.textContent = '🔊 Playing...';
            
            currentAudio = new Audio(file.url);
            
            currentAudio.onended = () => {
                file.played = true;
                itemEl.className = 'audio-item played';
                statusEl.textContent = '✅ Played';
                
                currentIndex++;
                updateQueueInfo();
                
                setTimeout(() => {
                    if (isPlaying) playNext();
                }, 500);
            };
            
            currentAudio.onerror = (error) => {
                statusEl.textContent = '❌ Error';
                console.error('Audio playback error:', error);
                currentIndex++;
                updateQueueInfo();
                setTimeout(() => {
                    if (isPlaying) playNext();
                }, 500);
            };
            
            currentAudio.play().catch(error => {
                console.error('Play error:', error);
                statusEl.textContent = '❌ Failed to play';
            });
            
            updateQueueInfo();
        }
        
        function stopPlayback() {
            isPlaying = false;
            
            if (currentAudio) {
                currentAudio.pause();
                currentAudio = null;
            }
            
            document.getElementById('playBtn').disabled = false;
            document.getElementById('stopBtn').disabled = true;
            
            const statusEl = document.getElementById('status');
            statusEl.className = 'status success';
            statusEl.textContent = `✅ Playback stopped. Played ${currentIndex} of ${audioFiles.length} files.`;
        }
        
        window.onload = loadAudioFiles;
    </script>
</body>
</html>
    """
    
    return HTMLResponse(content=html_content)


@app.get("/game/status/{username}")
def get_game_status(username: str):
    """
    Get the current game status for a user.
    This polls Lichess to check if the user is currently playing.
    """
    try:
        # Check if user is currently playing
        status_url = f"https://lichess.org/api/users/status"
        response = requests.get(
            status_url,
            params={"ids": username, "withGameIds": "true"},
            headers={"Accept": "application/json"},
            timeout=10
        )
        response.raise_for_status()
        
        data = response.json()
        if not data:
            return {"playing": False, "game_id": None}
        
        user_status = data[0]
        playing = user_status.get("playing", False)
        game_id = user_status.get("playingId")
        
        return {
            "playing": playing,
            "game_id": game_id,
            "username": username
        }
    except Exception as e:
        logging.error(f"Error checking game status: {e}")
        return {"error": str(e)}, 500

# ------------------
# WebSocket endpoint
# ------------------

@app.websocket("/ws/commentary/{game_id}")
async def websocket_endpoint(websocket: WebSocket, game_id: str):
    """
    WebSocket endpoint for receiving live commentary audio events.
    
    Path params:
        game_id: The lichess game ID to subscribe to
        
    Message format (server -> client):
    {
        "event": "commentary_audio",
        "game_id": "abc123",
        "move_number": 5,
        "latest_move": "e4",
        "commentary_text": "A bold opening move...",
        "audio_url": "/audio/Sat_Dec_27_002210_2025.mp3",
        "created_at_ms": 1703721730000
    }
    """
    logging.info(f"WebSocket connection request for game {game_id}")
    await connection_manager.connect(websocket, game_id)
    logging.info(f"WebSocket connection established for game {game_id}")
    
    try:
        # Keep connection alive and handle any incoming messages
        while True:
            # Wait for any message from client (e.g., ping/pong)
            data = await websocket.receive_text()
            # Echo back for now (can be used for heartbeat)
            await websocket.send_json({"type": "pong", "game_id": game_id})
    except WebSocketDisconnect:
        logging.info(f"WebSocket disconnected for game {game_id}")
        await connection_manager.disconnect(websocket, game_id)
    except Exception as e:
        logging.error(f"WebSocket error for game {game_id}: {e}")
        await connection_manager.disconnect(websocket, game_id)

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
