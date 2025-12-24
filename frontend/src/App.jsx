import { useState } from "react";

function App() {
  const [username, setUsername] = useState("");
  const [status, setStatus] = useState("idle");
  const [profile, setProfile] = useState(null);

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


return (
  <div className="min-h-screen flex items-center justify-center bg-gray-50">
    <div className="bg-white p-8 rounded-lg shadow-md w-full max-w-md">
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

      {status === "ready" && (
        <button className="w-full mt-4 border py-2 rounded bg-green-500 text-white">
          Start Live Game
        </button>
      )}
    </div>
  </div>
);

}

export default App;
