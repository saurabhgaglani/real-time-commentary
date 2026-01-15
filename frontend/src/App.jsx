import { useState } from "react";
import CommentaryPlayer from "./components/CommentaryPlayer.jsx";
import PlayerDashboard from "./components/PlayerDashboard.jsx";
import API_CONFIG from "./config/environment.js";

function App() {
  const [username, setUsername] = useState("");
  const [status, setStatus] = useState("idle");
  const [profile, setProfile] = useState(null);
  const [gameId, setGameId] = useState(null);
  const [isGameActive, setIsGameActive] = useState(false);

const analyzeUser = async () => {
  setStatus("analyzing");

  const res = await fetch(`${API_CONFIG.BACKEND_URL}${API_CONFIG.ENDPOINTS.ANALYZE}`, {
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
    const res = await fetch(`${API_CONFIG.BACKEND_URL}${API_CONFIG.ENDPOINTS.GAME_STATUS}/${username}`);
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
  <div className="min-h-screen bg-gradient-to-br from-gray-50 to-blue-50">
    <div className="container mx-auto px-4 py-8">
      {/* Header */}
      <div className="text-center mb-8">
        <h1 className="text-4xl font-bold text-gray-800 mb-2">
          Live Chess Commentary
        </h1>
        <p className="text-gray-600">
          AI-powered real-time chess game analysis and commentary
        </p>
      </div>

      {/* Main Input Section */}
      <div className="max-w-2xl mx-auto mb-8">
        <div className="bg-white rounded-xl shadow-lg p-8 border border-gray-100">
          <div className="space-y-6">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Chess.com Username
              </label>
              <input
                className="w-full border border-gray-300 rounded-lg px-4 py-3 focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-all"
                placeholder="Enter your chess.com username"
                value={username}
                onChange={(e) => setUsername(e.target.value)}
              />
            </div>

            <button
              className="w-full bg-gradient-to-r from-blue-600 to-purple-600 text-white py-3 px-6 rounded-lg font-semibold hover:from-blue-700 hover:to-purple-700 disabled:opacity-50 disabled:cursor-not-allowed transition-all"
              onClick={analyzeUser}
              disabled={!username || status === "analyzing"}
            >
              {status === "analyzing" ? "Analyzing Player..." : "Analyze Player"}
            </button>

            <div className="flex items-center justify-center">
              <div className="flex items-center gap-2">
                <div className={`w-2 h-2 rounded-full ${
                  status === "idle" ? "bg-gray-400" :
                  status === "analyzing" ? "bg-yellow-400 animate-pulse" :
                  status === "ready" ? "bg-green-400" : "bg-red-400"
                }`}></div>
                <span className="text-sm text-gray-600 capitalize">
                  {status === "analyzing" ? "Analyzing player profile..." : 
                   status === "ready" ? "Ready for live commentary" : status}
                </span>
              </div>
            </div>

            {status === "ready" && !isGameActive && (
              <button 
                className="w-full bg-gradient-to-r from-green-500 to-emerald-600 text-white py-3 px-6 rounded-lg font-semibold hover:from-green-600 hover:to-emerald-700 transition-all"
                onClick={startLiveGame}
              >
                🎙️ Start Live Commentary
              </button>
            )}

            {isGameActive && (
              <div className="space-y-4">
                <div className="bg-green-50 border border-green-200 rounded-lg p-4">
                  <div className="flex items-center gap-2 text-green-800">
                    <div className="w-2 h-2 bg-green-500 rounded-full animate-pulse"></div>
                    <span className="font-medium">Live commentary active</span>
                  </div>
                  <p className="text-sm text-green-700 mt-1">
                    Commentary is running in a new tab. Game ID: {gameId}
                  </p>
                </div>
                
                <button 
                  className="w-full bg-gradient-to-r from-red-500 to-red-600 text-white py-3 px-6 rounded-lg font-semibold hover:from-red-600 hover:to-red-700 transition-all"
                  onClick={stopLiveGame}
                >
                  Stop Live Commentary
                </button>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Player Dashboard */}
      {profile && (
        <div className="max-w-6xl mx-auto">
          <PlayerDashboard 
            profile={profile} 
            username={username}
            gameId={gameId}
            isGameActive={isGameActive}
          />
        </div>
      )}
    </div>
  </div>
);

}

export default App;