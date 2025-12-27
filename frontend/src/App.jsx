import { useState } from "react";
import CommentaryPlayer from "./components/CommentaryPlayer.jsx";

function App() {
  const [username, setUsername] = useState("");
  const [status, setStatus] = useState("idle");
  const [profile, setProfile] = useState(null);
  const [gameId, setGameId] = useState(null);
  const [isGameActive, setIsGameActive] = useState(false);

const analyzeUser = async () => {
  setStatus("analyzing");

  const res = await fetch("http://127.0.0.1:8000/analyze", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ username }),
  });

  const data = await res.json();

  setProfile(data.profile);
  setStatus(data.status);
};

const startLiveGame = async () => {
  // Fetch the current game_id from the backend
  try {
    setStatus("fetching_game");
    const res = await fetch(`http://127.0.0.1:8000/game/status/${username}`);
    const data = await res.json();
    
    if (data.playing && data.game_id) {
      setGameId(data.game_id);
      setIsGameActive(true);
      setStatus("ready");
    } else {
      alert("User is not currently playing a game on Lichess. Please start a game first.");
      setStatus("ready");
    }
  } catch (error) {
    console.error("Error fetching game status:", error);
    alert("Failed to fetch game status. Please try again.");
    setStatus("ready");
  }
};

const stopLiveGame = () => {
  setGameId(null);
  setIsGameActive(false);
};


return (
  <div className="min-h-screen flex items-center justify-center bg-gray-50 p-4">
    <div className="w-full max-w-4xl">
      <div className="bg-white p-8 rounded-lg shadow-md mb-4">
        <h1 className="text-2xl font-semibold mb-4">
          Live Chess Commentary
        </h1>

        <input
          className="w-full border rounded px-3 py-2 mb-4"
          placeholder="Enter chess.com username"
          value={username}
          onChange={(e) => setUsername(e.target.value)}
        />

        <button
          className="w-full bg-black text-white py-2 rounded disabled:opacity-50"
          onClick={analyzeUser}
          disabled={!username || status !== "idle"}
        >
          Analyze
        </button>

        <p className="text-sm text-gray-500 mt-4">
          Status: {status}
        </p>

        {profile && (
          <pre className="mt-4 text-xs bg-gray-100 p-2 rounded">
            {JSON.stringify(profile, null, 2)}
          </pre>
        )}

        {status === "ready" && !isGameActive && (
          <button 
            className="w-full mt-4 border py-2 rounded bg-green-500 text-white hover:bg-green-600 transition-colors"
            onClick={startLiveGame}
          >
            Start Live Game
          </button>
        )}

        {isGameActive && (
          <button 
            className="w-full mt-4 border py-2 rounded bg-red-500 text-white hover:bg-red-600 transition-colors"
            onClick={stopLiveGame}
          >
            Stop Live Game
          </button>
        )}
      </div>

      {/* Commentary Player - shown when game is active */}
      {isGameActive && gameId && (
        <div className="bg-white p-6 rounded-lg shadow-md">
          <h2 className="text-xl font-semibold mb-4 text-gray-800">
            Live Commentary
          </h2>
          <CommentaryPlayer gameId={gameId} />
        </div>
      )}
    </div>
  </div>
);

}

export default App;
