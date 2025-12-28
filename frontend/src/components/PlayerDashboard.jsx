import React, { useState } from 'react';
import LiveCommentaryView from './LiveCommentaryView.jsx';

/**
 * PlayerDashboard Component
 * 
 * Beautiful dashboard displaying player profile analysis with live game tab
 * 
 * @param {Object} props
 * @param {Object} props.profile - Player profile data
 * @param {string} props.username - Username
 * @param {string} props.gameId - Current game ID (if active)
 * @param {boolean} props.isGameActive - Whether live game is active
 */
function PlayerDashboard({ profile, username, gameId, isGameActive }) {
    const [activeTab, setActiveTab] = useState('profile');

    if (!profile) return null;

    const { identity, rating_narrative, behavior } = profile;

    const getRatingColor = (rating) => {
        if (rating >= 2200) return 'text-purple-600';
        if (rating >= 2000) return 'text-blue-600';
        if (rating >= 1800) return 'text-green-600';
        if (rating >= 1600) return 'text-yellow-600';
        return 'text-gray-600';
    };

    const getChangeColor = (change) => {
        if (change > 0) return 'text-green-600';
        if (change < 0) return 'text-red-600';
        return 'text-gray-600';
    };

    const formatChange = (change) => {
        if (change > 0) return `+${change}`;
        return change.toString();
    };

    const getWinRateColor = (winRate) => {
        if (winRate >= 60) return 'bg-green-500';
        if (winRate >= 50) return 'bg-yellow-500';
        return 'bg-red-500';
    };

    return (
        <div className="player-dashboard bg-gradient-to-br from-slate-50 to-blue-50 rounded-xl shadow-lg">
            {/* Header */}
            <div className="p-6 pb-0">
                <div className="flex items-center gap-4 mb-6">
                    <div className="w-16 h-16 bg-gradient-to-br from-blue-500 to-purple-600 rounded-full flex items-center justify-center text-white text-2xl font-bold">
                        {username.charAt(0).toUpperCase()}
                    </div>
                    <div>
                        <h2 className="text-3xl font-bold text-gray-800">{username}</h2>
                        <p className="text-gray-600">Chess Player Analysis</p>
                    </div>
                </div>

                {/* Tab Navigation */}
                <div className="flex border-b border-gray-200">
                    <button
                        onClick={() => setActiveTab('profile')}
                        className={`px-6 py-3 font-medium text-sm transition-colors ${
                            activeTab === 'profile'
                                ? 'text-blue-600 border-b-2 border-blue-600'
                                : 'text-gray-500 hover:text-gray-700'
                        }`}
                    >
                        📊 Player Profile
                    </button>
                    {isGameActive && (
                        <button
                            onClick={() => setActiveTab('live')}
                            className={`px-6 py-3 font-medium text-sm transition-colors flex items-center gap-2 ${
                                activeTab === 'live'
                                    ? 'text-green-600 border-b-2 border-green-600'
                                    : 'text-gray-500 hover:text-gray-700'
                            }`}
                        >
                            <div className="w-2 h-2 bg-green-500 rounded-full animate-pulse"></div>
                            🎙️ Live Commentary
                        </button>
                    )}
                </div>
            </div>

            {/* Tab Content */}
            <div className="p-6">
                {activeTab === 'profile' && (
                    <div className="profile-content">
                        {/* Ratings Section */}
                        <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
                            {/* Rapid Rating */}
                            <div className="bg-white rounded-lg p-6 shadow-md border border-gray-100">
                                <div className="flex items-center justify-between mb-4">
                                    <h3 className="text-lg font-semibold text-gray-700">Rapid</h3>
                                    <div className="w-3 h-3 bg-blue-500 rounded-full"></div>
                                </div>
                                <div className={`text-3xl font-bold mb-2 ${getRatingColor(identity.rapid_rating)}`}>
                                    {identity.rapid_rating}
                                </div>
                                <div className="text-sm text-gray-500 mb-3">
                                    {identity.rapid_games} games played
                                </div>
                                <div className="space-y-1 text-xs">
                                    <div className="flex justify-between">
                                        <span>Weekly:</span>
                                        <span className={getChangeColor(rating_narrative.rapid?.weekly_change || 0)}>
                                            {formatChange(rating_narrative.rapid?.weekly_change || 0)}
                                        </span>
                                    </div>
                                    <div className="flex justify-between">
                                        <span>Monthly:</span>
                                        <span className={getChangeColor(rating_narrative.rapid?.monthly_change || 0)}>
                                            {formatChange(rating_narrative.rapid?.monthly_change || 0)}
                                        </span>
                                    </div>
                                    <div className="flex justify-between">
                                        <span>Yearly:</span>
                                        <span className={getChangeColor(rating_narrative.rapid?.yearly_change || 0)}>
                                            {formatChange(rating_narrative.rapid?.yearly_change || 0)}
                                        </span>
                                    </div>
                                </div>
                            </div>

                            {/* Blitz Rating */}
                            <div className="bg-white rounded-lg p-6 shadow-md border border-gray-100">
                                <div className="flex items-center justify-between mb-4">
                                    <h3 className="text-lg font-semibold text-gray-700">Blitz</h3>
                                    <div className="w-3 h-3 bg-orange-500 rounded-full"></div>
                                </div>
                                <div className={`text-3xl font-bold mb-2 ${getRatingColor(identity.blitz_rating)}`}>
                                    {identity.blitz_rating}
                                </div>
                                <div className="text-sm text-gray-500 mb-3">
                                    {identity.blitz_games} games played
                                </div>
                                <div className="space-y-1 text-xs">
                                    <div className="flex justify-between">
                                        <span>Weekly:</span>
                                        <span className={getChangeColor(rating_narrative.blitz?.weekly_change || 0)}>
                                            {formatChange(rating_narrative.blitz?.weekly_change || 0)}
                                        </span>
                                    </div>
                                    <div className="flex justify-between">
                                        <span>Monthly:</span>
                                        <span className={getChangeColor(rating_narrative.blitz?.monthly_change || 0)}>
                                            {formatChange(rating_narrative.blitz?.monthly_change || 0)}
                                        </span>
                                    </div>
                                    <div className="flex justify-between">
                                        <span>Yearly:</span>
                                        <span className={getChangeColor(rating_narrative.blitz?.yearly_change || 0)}>
                                            {formatChange(rating_narrative.blitz?.yearly_change || 0)}
                                        </span>
                                    </div>
                                </div>
                            </div>

                            {/* Player Stats */}
                            <div className="bg-white rounded-lg p-6 shadow-md border border-gray-100">
                                <div className="flex items-center justify-between mb-4">
                                    <h3 className="text-lg font-semibold text-gray-700">Style</h3>
                                    <div className="w-3 h-3 bg-green-500 rounded-full"></div>
                                </div>
                                <div className="text-2xl font-bold mb-2 text-green-600 capitalize">
                                    {behavior.style}
                                </div>
                                <div className="text-sm text-gray-500 mb-3">
                                    Avg game: {behavior.average_game_length} moves
                                </div>
                                <div className="space-y-2 text-xs">
                                    <div className="flex justify-between">
                                        <span>White opens:</span>
                                        <span className="font-medium">{behavior.white.preferred_first_move}</span>
                                    </div>
                                    <div className="flex justify-between">
                                        <span>Black responds:</span>
                                        <span className="font-medium">{behavior.black.preferred_first_move}</span>
                                    </div>
                                </div>
                            </div>
                        </div>

                        {/* Opening Repertoire */}
                        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-6">
                            {/* White Openings */}
                            <div className="bg-white rounded-lg p-6 shadow-md border border-gray-100">
                                <div className="flex items-center gap-2 mb-4">
                                    <div className="w-4 h-4 bg-white border-2 border-gray-800 rounded-sm"></div>
                                    <h3 className="text-lg font-semibold text-gray-700">White Repertoire</h3>
                                </div>
                                <div className="space-y-3">
                                    {behavior.white.top_openings.slice(0, 5).map((opening, index) => (
                                        <div key={index} className="flex items-center justify-between p-3 bg-gray-50 rounded-lg">
                                            <div className="flex-1">
                                                <div className="font-medium text-sm text-gray-800 mb-1">
                                                    {opening.name}
                                                </div>
                                                <div className="text-xs text-gray-500">
                                                    {opening.games_played} games
                                                </div>
                                            </div>
                                            <div className="flex items-center gap-2">
                                                <div className={`w-2 h-2 rounded-full ${getWinRateColor(opening.win_rate_pct)}`}></div>
                                                <span className="text-sm font-semibold text-gray-700">
                                                    {opening.win_rate_pct}%
                                                </span>
                                            </div>
                                        </div>
                                    ))}
                                </div>
                            </div>

                            {/* Black Openings */}
                            <div className="bg-white rounded-lg p-6 shadow-md border border-gray-100">
                                <div className="flex items-center gap-2 mb-4">
                                    <div className="w-4 h-4 bg-gray-800 rounded-sm"></div>
                                    <h3 className="text-lg font-semibold text-gray-700">Black Repertoire</h3>
                                </div>
                                <div className="space-y-3">
                                    {behavior.black.top_openings.slice(0, 5).map((opening, index) => (
                                        <div key={index} className="flex items-center justify-between p-3 bg-gray-50 rounded-lg">
                                            <div className="flex-1">
                                                <div className="font-medium text-sm text-gray-800 mb-1">
                                                    {opening.name}
                                                </div>
                                                <div className="text-xs text-gray-500">
                                                    {opening.games_played} games
                                                </div>
                                            </div>
                                            <div className="flex items-center gap-2">
                                                <div className={`w-2 h-2 rounded-full ${getWinRateColor(opening.win_rate_pct)}`}></div>
                                                <span className="text-sm font-semibold text-gray-700">
                                                    {opening.win_rate_pct}%
                                                </span>
                                            </div>
                                        </div>
                                    ))}
                                </div>
                            </div>
                        </div>

                        {/* Recent Results */}
                        <div className="bg-white rounded-lg p-6 shadow-md border border-gray-100">
                            <h3 className="text-lg font-semibold text-gray-700 mb-4">Recent Results</h3>
                            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                                <div className="flex items-center justify-between p-3 bg-gray-50 rounded-lg">
                                    <div className="flex items-center gap-3">
                                        <div className="w-4 h-4 bg-white border-2 border-gray-800 rounded-sm"></div>
                                        <span className="text-sm font-medium">Last White Game</span>
                                    </div>
                                    <div className="flex items-center gap-2">
                                        <span className="text-xs text-gray-500 capitalize">
                                            {behavior.white.last_result.time_control}
                                        </span>
                                        <span className={`text-sm font-semibold ${
                                            behavior.white.last_result.result === 'win' ? 'text-green-600' :
                                            behavior.white.last_result.result === 'loss' ? 'text-red-600' : 'text-yellow-600'
                                        }`}>
                                            {behavior.white.last_result.result.toUpperCase()}
                                        </span>
                                    </div>
                                </div>
                                <div className="flex items-center justify-between p-3 bg-gray-50 rounded-lg">
                                    <div className="flex items-center gap-3">
                                        <div className="w-4 h-4 bg-gray-800 rounded-sm"></div>
                                        <span className="text-sm font-medium">Last Black Game</span>
                                    </div>
                                    <div className="flex items-center gap-2">
                                        <span className="text-xs text-gray-500 capitalize">
                                            {behavior.black.last_result.time_control}
                                        </span>
                                        <span className={`text-sm font-semibold ${
                                            behavior.black.last_result.result === 'win' ? 'text-green-600' :
                                            behavior.black.last_result.result === 'loss' ? 'text-red-600' : 'text-yellow-600'
                                        }`}>
                                            {behavior.black.last_result.result.toUpperCase()}
                                        </span>
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>
                )}

                {activeTab === 'live' && isGameActive && gameId && (
                    <div className="live-content">
                        <div className="bg-gradient-to-br from-slate-900 via-slate-800 to-slate-900 rounded-xl p-6 text-white">
                            <LiveCommentaryView gameId={gameId} username={username} />
                        </div>
                    </div>
                )}
            </div>
        </div>
    );
}

export default PlayerDashboard;