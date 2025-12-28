import React from 'react';
import LiveCommentaryView from './components/LiveCommentaryView.jsx';

/**
 * LiveCommentaryPage Component
 * 
 * Standalone page for live commentary (opened in new tab)
 */
function LiveCommentaryPage() {
    // Get URL parameters
    const urlParams = new URLSearchParams(window.location.search);
    const gameId = urlParams.get('gameId');
    const username = urlParams.get('username');

    if (!gameId || !username) {
        return (
            <div className="min-h-screen bg-gradient-to-br from-slate-900 to-slate-800 flex items-center justify-center text-white">
                <div className="text-center">
                    <h1 className="text-2xl font-bold mb-4">Invalid Parameters</h1>
                    <p className="text-gray-400">Missing gameId or username parameters.</p>
                </div>
            </div>
        );
    }

    return <LiveCommentaryView gameId={gameId} username={username} />;
}

export default LiveCommentaryPage;