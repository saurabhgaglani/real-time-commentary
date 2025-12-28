import React from 'react';
import useCommentary from '../hooks/useCommentary.js';

/**
 * CommentaryPlayer Component
 * 
 * Displays live chess commentary with connection status, current commentary,
 * queue information, and error messages.
 * 
 * @param {Object} props
 * @param {string} props.gameId - The lichess game ID to receive commentary for
 */
function CommentaryPlayer({ gameId }) {
    const {
        isConnected,
        connectionStatus,
        currentCommentary,
        queueLength,
        error
    } = useCommentary(gameId);

    /**
     * Get status indicator styling based on connection status
     */
    const getStatusStyle = () => {
        switch (connectionStatus) {
            case 'connected':
                return 'bg-green-500';
            case 'connecting':
            case 'reconnecting':
                return 'bg-yellow-500';
            case 'disconnected':
                return 'bg-gray-500';
            case 'error':
                return 'bg-red-500';
            default:
                return 'bg-gray-500';
        }
    };

    /**
     * Get status text based on connection status
     */
    const getStatusText = () => {
        switch (connectionStatus) {
            case 'connected':
                return 'Connected';
            case 'connecting':
                return 'Connecting...';
            case 'reconnecting':
                return 'Reconnecting...';
            case 'disconnected':
                return 'Disconnected';
            case 'error':
                return 'Connection Error';
            default:
                return 'Unknown';
        }
    };

    if (!gameId) {
        return null;
    }

    return (
        <div className="commentary-player bg-gray-800 rounded-lg p-4 shadow-lg">
            {/* Connection Status Indicator */}
            <div className="flex items-center gap-2 mb-4">
                <div className={`w-3 h-3 rounded-full ${getStatusStyle()}`}></div>
                <span className="text-sm font-medium text-gray-300">
                    {getStatusText()}
                </span>
            </div>

            {/* Current Commentary Display */}
            {currentCommentary && (
                <div className="current-commentary bg-gray-700 rounded-md p-4 mb-3">
                    <div className="move-info text-sm text-gray-400 mb-2">
                        Move {currentCommentary.moveNumber}: <span className="font-semibold text-white">{currentCommentary.latestMove}</span>
                    </div>
                    <div className="commentary-text text-base text-gray-100 leading-relaxed">
                        {currentCommentary.text}
                    </div>
                    {currentCommentary.isPlaying && (
                        <div className="playing-indicator flex items-center gap-2 mt-3 text-sm text-blue-400">
                            <span className="animate-pulse">🔊</span>
                            <span>Playing...</span>
                        </div>
                    )}
                </div>
            )}

            {/* Queue Status */}
            {queueLength > 0 && (
                <div className="queue-status bg-blue-900 bg-opacity-30 rounded-md p-2 mb-3">
                    <span className="text-sm text-blue-300">
                        {queueLength} {queueLength === 1 ? 'commentary' : 'commentaries'} in queue
                    </span>
                </div>
            )}

            {/* Error Display */}
            {error && (
                <div className="error-message bg-red-900 bg-opacity-30 border border-red-500 rounded-md p-3">
                    <div className="flex items-start gap-2">
                        <span className="text-red-400 text-lg">⚠️</span>
                        <span className="text-sm text-red-300">{error}</span>
                    </div>
                </div>
            )}

            {/* Empty State */}
            {!currentCommentary && !error && isConnected && (
                <div className="empty-state text-center py-6 text-gray-500 text-sm">
                    Waiting for commentary...
                </div>
            )}
        </div>
    );
}

export default CommentaryPlayer;
