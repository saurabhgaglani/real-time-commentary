import React, { useState, useEffect, useRef } from 'react';
import CommentaryChessBoard from './CommentaryChessBoard.jsx';
import useCommentary from '../hooks/useCommentary.js';

/**
 * LiveCommentaryView Component
 * 
 * Full-screen live commentary interface - better than Lichess!
 * 
 * @param {Object} props
 * @param {string} props.gameId - The lichess game ID
 * @param {string} props.username - The username being followed
 */
function LiveCommentaryView({ gameId, username }) {
    const {
        isConnected,
        connectionStatus,
        currentCommentary,
        queueLength,
        error
    } = useCommentary(gameId);

    const [gameInfo, setGameInfo] = useState(null);
    const [timeRemaining, setTimeRemaining] = useState({ white: null, black: null });
    const [lastMoveTime, setLastMoveTime] = useState(null);
    const [currentTurn, setCurrentTurn] = useState('white');
    const [isTimerRunning, setIsTimerRunning] = useState(false);
    
    // Timer refs
    const timerIntervalRef = useRef(null);
    const lastUpdateTimeRef = useRef(null);

    // Fetch game info for player names, ratings, etc.
    useEffect(() => {
        const fetchGameInfo = async () => {
            try {
                const response = await fetch(`https://lichess.org/api/user/${username}/current-game`);
                if (response.ok) {
                    const data = await response.json();
                    setGameInfo(data);
                    
                    // Set initial time if available
                    if (data.clock) {
                        const initialWhiteTime = data.clock.white || 600; // Default 10 minutes
                        const initialBlackTime = data.clock.black || 600;
                        
                        setTimeRemaining({
                            white: initialWhiteTime,
                            black: initialBlackTime
                        });
                        
                        // Determine whose turn it is based on move count
                        const moves = data.moves ? data.moves.split(' ').filter(m => m.trim()) : [];
                        const isWhiteTurn = moves.length % 2 === 0;
                        setCurrentTurn(isWhiteTurn ? 'white' : 'black');
                        
                        console.log('🕐 Initial timer setup:', {
                            white: initialWhiteTime,
                            black: initialBlackTime,
                            turn: isWhiteTurn ? 'white' : 'black',
                            moves: moves.length
                        });
                    }
                }
            } catch (error) {
                console.error('Error fetching game info:', error);
            }
        };

        if (username) {
            fetchGameInfo();
            // Refresh game info every 30 seconds for time sync
            const interval = setInterval(fetchGameInfo, 30000);
            return () => clearInterval(interval);
        }
    }, [username]);

    // Timer management based on commentary moves
    useEffect(() => {
        if (currentCommentary && timeRemaining.white !== null && timeRemaining.black !== null) {
            const moveNumber = currentCommentary.moveNumber;
            
            // Stop timer when new move commentary arrives
            if (timerIntervalRef.current) {
                clearInterval(timerIntervalRef.current);
                timerIntervalRef.current = null;
                setIsTimerRunning(false);
                console.log('⏸️ Timer stopped for new move commentary');
            }
            
            // Update whose turn it is based on move number
            const isWhiteTurn = moveNumber % 2 === 1; // Odd moves = white's turn next
            const newTurn = isWhiteTurn ? 'white' : 'black';
            setCurrentTurn(newTurn);
            setLastMoveTime(Date.now());
            
            console.log('🎯 Move commentary received:', {
                moveNumber,
                nextTurn: newTurn,
                whiteTime: timeRemaining.white,
                blackTime: timeRemaining.black
            });
            
            // Start timer for the player whose turn it is
            setTimeout(() => {
                startTimer(newTurn);
            }, 1000); // Small delay to show the move was played
        }
    }, [currentCommentary, timeRemaining.white, timeRemaining.black]);

    // Start countdown timer for current player
    const startTimer = (playerColor) => {
        if (timerIntervalRef.current) {
            clearInterval(timerIntervalRef.current);
        }
        
        setIsTimerRunning(true);
        lastUpdateTimeRef.current = Date.now();
        
        console.log(`▶️ Starting timer for ${playerColor}`);
        
        timerIntervalRef.current = setInterval(() => {
            const now = Date.now();
            const elapsed = Math.floor((now - lastUpdateTimeRef.current) / 1000);
            
            if (elapsed >= 1) {
                setTimeRemaining(prev => {
                    const newTime = { ...prev };
                    newTime[playerColor] = Math.max(0, newTime[playerColor] - elapsed);
                    
                    // Stop timer if time runs out
                    if (newTime[playerColor] <= 0) {
                        clearInterval(timerIntervalRef.current);
                        timerIntervalRef.current = null;
                        setIsTimerRunning(false);
                        console.log(`⏰ Time up for ${playerColor}!`);
                    }
                    
                    return newTime;
                });
                
                lastUpdateTimeRef.current = now;
            }
        }, 100); // Update every 100ms for smooth countdown
    };

    // Cleanup timer on unmount
    useEffect(() => {
        return () => {
            if (timerIntervalRef.current) {
                clearInterval(timerIntervalRef.current);
            }
        };
    }, []);

    const formatTime = (seconds) => {
        if (!seconds) return '--:--';
        const mins = Math.floor(seconds / 60);
        const secs = seconds % 60;
        return `${mins}:${secs.toString().padStart(2, '0')}`;
    };

    const getStatusColor = () => {
        switch (connectionStatus) {
            case 'connected': return 'bg-green-500';
            case 'connecting':
            case 'reconnecting': return 'bg-yellow-500';
            case 'disconnected': return 'bg-gray-500';
            case 'error': return 'bg-red-500';
            default: return 'bg-gray-500';
        }
    };

    const getStatusText = () => {
        switch (connectionStatus) {
            case 'connected': return 'Live';
            case 'connecting': return 'Connecting...';
            case 'reconnecting': return 'Reconnecting...';
            case 'disconnected': return 'Disconnected';
            case 'error': return 'Error';
            default: return 'Unknown';
        }
    };

    return (
        <div className="live-commentary-view min-h-screen bg-gradient-to-br from-slate-900 via-slate-800 to-slate-900 text-white">
            {/* Header */}
            <div className="bg-black/20 backdrop-blur-sm border-b border-white/10 p-4">
                <div className="max-w-7xl mx-auto flex items-center justify-between">
                    <div className="flex items-center gap-4">
                        <div className="flex items-center gap-2">
                            <div className={`w-3 h-3 rounded-full ${getStatusColor()} animate-pulse`}></div>
                            <span className="text-sm font-medium">{getStatusText()}</span>
                        </div>
                        <div className="h-6 w-px bg-white/20"></div>
                        <h1 className="text-xl font-bold">Live Chess Commentary</h1>
                    </div>
                    
                    {queueLength > 0 && (
                        <div className="flex items-center gap-2 bg-blue-500/20 px-3 py-1 rounded-full">
                            <div className="w-2 h-2 bg-blue-400 rounded-full animate-pulse"></div>
                            <span className="text-sm">{queueLength} in queue</span>
                        </div>
                    )}
                </div>
            </div>

            <div className="max-w-7xl mx-auto p-6">
                <div className="grid grid-cols-1 xl:grid-cols-3 gap-6 h-full">
                    {/* Left Column - Game Info & Players */}
                    <div className="xl:col-span-1 space-y-6">
                        {/* Players */}
                        {gameInfo && (
                            <div className="bg-white/5 backdrop-blur-sm rounded-xl p-6 border border-white/10">
                                <h2 className="text-lg font-semibold mb-4 text-center">Players</h2>
                                
                                {/* White Player */}
                                <div className={`mb-4 p-4 rounded-lg transition-all ${
                                    currentTurn === 'white' && isTimerRunning 
                                        ? 'bg-yellow-500/20 border-2 border-yellow-500' 
                                        : 'bg-white/5'
                                }`}>
                                    <div className="flex items-center justify-between mb-2">
                                        <div className="flex items-center gap-3">
                                            <div className="w-6 h-6 bg-white rounded border-2 border-gray-600"></div>
                                            <div>
                                                <div className="font-semibold">
                                                    {gameInfo.players?.white?.user?.name || 'White'}
                                                    {gameInfo.players?.white?.user?.name?.toLowerCase() === username.toLowerCase() && (
                                                        <span className="ml-2 text-xs bg-blue-500 px-2 py-1 rounded-full">Following</span>
                                                    )}
                                                </div>
                                                <div className="text-sm text-gray-300">
                                                    {gameInfo.players?.white?.rating || '?'}
                                                </div>
                                            </div>
                                        </div>
                                        <div className="text-right">
                                            <div className={`text-lg font-mono transition-colors ${
                                                currentTurn === 'white' && isTimerRunning 
                                                    ? 'text-yellow-400 animate-pulse' 
                                                    : 'text-white'
                                            }`}>
                                                {formatTime(timeRemaining.white)}
                                            </div>
                                            {currentTurn === 'white' && isTimerRunning && (
                                                <div className="text-xs text-yellow-400">
                                                    ⏱️ Thinking...
                                                </div>
                                            )}
                                        </div>
                                    </div>
                                </div>

                                {/* VS Divider */}
                                <div className="text-center py-2">
                                    <span className="text-gray-400 font-bold">VS</span>
                                </div>

                                {/* Black Player */}
                                <div className={`p-4 rounded-lg transition-all ${
                                    currentTurn === 'black' && isTimerRunning 
                                        ? 'bg-yellow-500/20 border-2 border-yellow-500' 
                                        : 'bg-white/5'
                                }`}>
                                    <div className="flex items-center justify-between mb-2">
                                        <div className="flex items-center gap-3">
                                            <div className="w-6 h-6 bg-gray-800 rounded border-2 border-gray-400"></div>
                                            <div>
                                                <div className="font-semibold">
                                                    {gameInfo.players?.black?.user?.name || 'Black'}
                                                    {gameInfo.players?.black?.user?.name?.toLowerCase() === username.toLowerCase() && (
                                                        <span className="ml-2 text-xs bg-blue-500 px-2 py-1 rounded-full">Following</span>
                                                    )}
                                                </div>
                                                <div className="text-sm text-gray-300">
                                                    {gameInfo.players?.black?.rating || '?'}
                                                </div>
                                            </div>
                                        </div>
                                        <div className="text-right">
                                            <div className={`text-lg font-mono transition-colors ${
                                                currentTurn === 'black' && isTimerRunning 
                                                    ? 'text-yellow-400 animate-pulse' 
                                                    : 'text-white'
                                            }`}>
                                                {formatTime(timeRemaining.black)}
                                            </div>
                                            {currentTurn === 'black' && isTimerRunning && (
                                                <div className="text-xs text-yellow-400">
                                                    ⏱️ Thinking...
                                                </div>
                                            )}
                                        </div>
                                    </div>
                                </div>

                                {/* Game Info */}
                                <div className="mt-4 pt-4 border-t border-white/10">
                                    <div className="grid grid-cols-2 gap-4 text-sm">
                                        <div>
                                            <span className="text-gray-400">Time Control:</span>
                                            <div className="font-medium capitalize">{gameInfo.speed || 'Unknown'}</div>
                                        </div>
                                        <div>
                                            <span className="text-gray-400">Rated:</span>
                                            <div className="font-medium">{gameInfo.rated ? 'Yes' : 'No'}</div>
                                        </div>
                                        <div>
                                            <span className="text-gray-400">Status:</span>
                                            <div className="font-medium capitalize">{gameInfo.status || 'Unknown'}</div>
                                        </div>
                                        <div>
                                            <span className="text-gray-400">Game ID:</span>
                                            <div className="font-mono text-xs">{gameId}</div>
                                        </div>
                                    </div>
                                </div>
                            </div>
                        )}

                        {/* Current Commentary */}
                        <div className="bg-white/5 backdrop-blur-sm rounded-xl p-6 border border-white/10">
                            <h2 className="text-lg font-semibold mb-4">Live Commentary</h2>
                            
                            {currentCommentary ? (
                                <div className="space-y-4">
                                    <div className="flex items-center justify-between text-sm text-gray-300">
                                        <span>Move {Math.ceil(currentCommentary.moveNumber / 2)}</span>
                                        <span className="font-mono">{currentCommentary.latestMove}</span>
                                    </div>
                                    
                                    <div className="bg-white/5 rounded-lg p-4">
                                        <p className="text-gray-100 leading-relaxed">
                                            {currentCommentary.text}
                                        </p>
                                    </div>
                                    
                                    {currentCommentary.isPlaying && (
                                        <div className="flex items-center gap-2 text-blue-400">
                                            <div className="w-2 h-2 bg-blue-400 rounded-full animate-pulse"></div>
                                            <span className="text-sm">Playing audio...</span>
                                        </div>
                                    )}
                                </div>
                            ) : (
                                <div className="text-center py-8 text-gray-400">
                                    <div className="w-12 h-12 mx-auto mb-3 bg-white/10 rounded-full flex items-center justify-center">
                                        <span className="text-xl">🎙️</span>
                                    </div>
                                    <p>Waiting for commentary...</p>
                                </div>
                            )}
                        </div>

                        {/* Error Display */}
                        {error && (
                            <div className="bg-red-500/20 border border-red-500/30 rounded-xl p-4">
                                <div className="flex items-center gap-2 text-red-400">
                                    <span className="text-lg">⚠️</span>
                                    <span className="font-medium">Connection Error</span>
                                </div>
                                <p className="text-sm text-red-300 mt-2">{error}</p>
                            </div>
                        )}
                    </div>

                    {/* Center Column - Chess Board */}
                    <div className="xl:col-span-2">
                        <div className="bg-white/5 backdrop-blur-sm rounded-xl p-6 border border-white/10 h-full">
                            <CommentaryChessBoard 
                                currentCommentary={currentCommentary}
                                gameId={gameId}
                                username={username}
                            />
                        </div>
                    </div>
                </div>
            </div>
        </div>
    );
}

export default LiveCommentaryView;