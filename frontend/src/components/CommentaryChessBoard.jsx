import React, { useState, useEffect, useRef } from 'react';
import { Chessboard } from 'react-chessboard';
import { Chess } from 'chess.js';

/**
 * CommentaryChessBoard Component
 * 
 * Fetches PGN from Lichess, converts to move list, then builds incrementally
 * 
 * @param {Object} props
 * @param {Object} props.currentCommentary - Current commentary object with move info
 * @param {string} props.gameId - The lichess game ID
 * @param {string} props.username - The username of the player being followed
 */
function CommentaryChessBoard({ currentCommentary, gameId, username }) {
    const [game, setGame] = useState(new Chess());
    const [boardPosition, setBoardPosition] = useState('start');
    const [lastProcessedMove, setLastProcessedMove] = useState(0);
    const [isInitialized, setIsInitialized] = useState(false);
    const [moveHistory, setMoveHistory] = useState([]);
    const [playerColor, setPlayerColor] = useState('white');
    const [error, setError] = useState(null);
    const [lastMoveSquares, setLastMoveSquares] = useState({ from: null, to: null });
    
    // Store the complete move list from PGN (fetch once, use many times)
    const gameMoveListRef = useRef([]);
    const initialSetupRef = useRef(false);
    const lastFetchedGameRef = useRef(null);

    // Debug logging
    console.log('🔍 CommentaryChessBoard render:', {
        gameId,
        username,
        hasCommentary: !!currentCommentary,
        isInitialized,
        boardPosition: boardPosition.substring(0, 20) + '...',
        lastProcessedMove
    });

    /**
     * Fetch current game using the correct Lichess API
     */
    const fetchGameMoves = async () => {
        try {
            console.log(`Fetching current game for username: ${username}`);
            
            const response = await fetch(`https://lichess.org/api/user/${username}/current-game`, {
                headers: {
                    'Accept': 'application/json'
                }
            });
            
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }
            
            const gameData = await response.json();
            console.log('Received current game data:', gameData);
            
            // Validate we have the expected data structure
            if (!gameData || typeof gameData !== 'object') {
                throw new Error('Invalid game data received');
            }
            
            // Extract moves from the "moves" field (space-separated string)
            let moves = [];
            if (gameData.moves && typeof gameData.moves === 'string') {
                moves = gameData.moves.split(' ').filter(m => m && m.trim());
            }
            
            // Determine player color with fallback
            let playerColor = 'white';
            try {
                const whiteName = gameData.players?.white?.user?.name;
                const blackName = gameData.players?.black?.user?.name;
                
                if (whiteName && whiteName.toLowerCase() === username.toLowerCase()) {
                    playerColor = 'white';
                } else if (blackName && blackName.toLowerCase() === username.toLowerCase()) {
                    playerColor = 'black';
                }
            } catch (colorError) {
                console.warn('Could not determine player color, defaulting to white:', colorError);
            }
            
            console.log(`✅ SUCCESS: Player ${username} is ${playerColor}, ${moves.length} moves available`);
            console.log('Moves:', moves.slice(0, 10), moves.length > 10 ? `... and ${moves.length - 10} more` : '');
            
            return {
                moves,
                playerColor,
                success: true
            };
            
        } catch (error) {
            console.error('❌ ERROR fetching current game:', error);
            return {
                moves: [],
                playerColor: 'white',
                success: false,
                error: error.message
            };
        }
    };

    /**
     * Build game incrementally from current position to target move
     */
    const buildGameIncrementally = (targetMoveNumber) => {
        try {
            console.log(`🔨 Building game incrementally to move ${targetMoveNumber}`);
            console.log(`📋 Available moves: ${gameMoveListRef.current.length}`);
            console.log(`🎯 Target vs Current: ${targetMoveNumber} vs ${lastProcessedMove}`);
            
            // Always rebuild from scratch to ensure accuracy
            console.log('🔄 Rebuilding from scratch for accuracy');
            const newGame = new Chess();
            const newMoveHistory = [];
            let lastMoveInfo = { from: null, to: null };
            
            // Play all moves up to target
            for (let i = 0; i < targetMoveNumber && i < gameMoveListRef.current.length; i++) {
                const moveStr = gameMoveListRef.current[i];
                
                if (!moveStr || moveStr.trim() === '') {
                    console.warn(`⚠️ Skipping empty move at position ${i + 1}`);
                    continue;
                }
                
                try {
                    const moveResult = newGame.move(moveStr);
                    if (moveResult) {
                        newMoveHistory.push({
                            move: moveResult.san,
                            fen: newGame.fen(),
                            moveNumber: Math.ceil((i + 1) / 2)
                        });
                        
                        // Capture the last move's squares for highlighting
                        if (i === targetMoveNumber - 1) {
                            lastMoveInfo = {
                                from: moveResult.from,
                                to: moveResult.to
                            };
                            console.log(`🎯 Last move squares: ${moveResult.from} -> ${moveResult.to}`);
                        }
                        
                        console.log(`✓ Move ${i + 1}: ${moveStr} -> ${moveResult.san}`);
                    } else {
                        console.error(`❌ Could not apply move ${i + 1}: ${moveStr}`);
                        // Don't break, try to continue with remaining moves
                    }
                } catch (moveError) {
                    console.error(`💥 Error applying move ${i + 1}: ${moveStr}`, moveError);
                    // Don't break, try to continue with remaining moves
                }
            }
            
            console.log(`🏁 Build complete. Final position: ${newGame.fen()}`);
            console.log(`📊 Processed ${newMoveHistory.length} moves successfully`);
            
            return {
                game: newGame,
                moveHistory: newMoveHistory,
                lastMoveSquares: lastMoveInfo,
                success: true
            };
            
        } catch (error) {
            console.error('💥 Error in incremental build:', error);
            return {
                game: new Chess(),
                moveHistory: [],
                lastMoveSquares: { from: null, to: null },
                success: false,
                error: error.message
            };
        }
    };

    /**
     * Initialize the board when gameId and username are available
     */
    useEffect(() => {
        // Initialize if we have gameId/username but haven't initialized yet
        const shouldInitialize = gameId && username && !initialSetupRef.current;
        
        if (shouldInitialize) {
            console.log('🚀 Initializing chess board - gameId:', gameId, 'username:', username);
            initialSetupRef.current = true;
            setIsInitialized(true);
            setError(null);
            
            // Fetch the complete move list and initialize
            const initializeGame = async () => {
                console.log('📡 Fetching game moves for initialization...');
                const { moves, playerColor, success, error: fetchError } = await fetchGameMoves();
                
                if (success) {
                    gameMoveListRef.current = moves;
                    setPlayerColor(playerColor);
                    lastFetchedGameRef.current = gameId;
                    console.log('✅ Game initialized successfully:');
                    console.log(`   - Total moves: ${moves.length}`);
                    console.log(`   - Player color: ${playerColor}`);
                    
                    // Always show the current live position initially
                    let targetMoveNumber = moves.length; // Show current live position
                    
                    console.log(`🎯 Showing live position: ${moves.length} moves`);
                    
                    // Build the position
                    if (targetMoveNumber > 0) {
                        const { game: newGame, moveHistory: newMoveHistory, lastMoveSquares: moveSquares, success: buildSuccess } = buildGameIncrementally(targetMoveNumber);
                        
                        if (buildSuccess) {
                            setGame(newGame);
                            setBoardPosition(newGame.fen());
                            setMoveHistory(newMoveHistory);
                            setLastMoveSquares(moveSquares);
                            setLastProcessedMove(targetMoveNumber);
                            console.log('✅ Live position set successfully');
                        }
                    } else {
                        // Starting position
                        const newGame = new Chess();
                        setGame(newGame);
                        setBoardPosition(newGame.fen());
                        setMoveHistory([]);
                        setLastMoveSquares({ from: null, to: null });
                        setLastProcessedMove(0);
                        console.log('✅ Starting position set');
                    }
                } else {
                    console.error('❌ Failed to initialize game:', fetchError);
                    setError(`Failed to fetch game: ${fetchError}`);
                    
                    // Fallback to starting position so board still shows
                    const newGame = new Chess();
                    setGame(newGame);
                    setBoardPosition(newGame.fen());
                    setMoveHistory([]);
                    setLastMoveSquares({ from: null, to: null });
                    setLastProcessedMove(0);
                    console.log('⚠️ Fallback to starting position');
                }
            };
            
            initializeGame();
        }
    }, [gameId, username]); // Only depend on gameId and username

    /**
     * Update board when commentary arrives (but board is already initialized)
     */
    useEffect(() => {
        if (!currentCommentary || !isInitialized || !username) return;
        
        const currentMoveNumber = currentCommentary.moveNumber;
        const latestMove = currentCommentary.latestMove;
        
        console.log(`🎯 COMMENTARY RECEIVED:`);
        console.log(`   - Move Number: ${currentMoveNumber}`);
        console.log(`   - Latest Move: ${latestMove}`);
        console.log(`   - Last Processed: ${lastProcessedMove}`);
        console.log(`   - Available Moves: ${gameMoveListRef.current.length}`);
        
        // Check if commentary is ahead of our move list - need to refresh API data
        if (currentMoveNumber > gameMoveListRef.current.length) {
            console.log(`🔄 COMMENTARY AHEAD OF API DATA - Refreshing move list`);
            console.log(`   - Commentary at move ${currentMoveNumber}, API has ${gameMoveListRef.current.length} moves`);
            
            // Refresh the move list from API
            const refreshMoves = async () => {
                const { moves, playerColor, success, error: fetchError } = await fetchGameMoves();
                
                if (success && moves.length >= currentMoveNumber) {
                    console.log(`✅ REFRESHED MOVES: Now have ${moves.length} moves`);
                    gameMoveListRef.current = moves;
                    setPlayerColor(playerColor);
                    
                    // Now build the position with updated moves
                    const { game: newGame, moveHistory: newMoveHistory, lastMoveSquares: moveSquares, success: buildSuccess, error: buildError } = buildGameIncrementally(currentMoveNumber);
                    
                    if (buildSuccess) {
                        console.log(`📍 Setting new position: ${newGame.fen()}`);
                        setGame(newGame);
                        setBoardPosition(newGame.fen());
                        setMoveHistory(newMoveHistory);
                        setLastMoveSquares(moveSquares);
                        setLastProcessedMove(currentMoveNumber);
                        setError(null);
                        
                        console.log(`✅ BOARD UPDATED WITH REFRESHED DATA`);
                    } else {
                        console.error(`❌ FAILED TO BUILD WITH REFRESHED DATA: ${buildError}`);
                        setError(`Failed to build position: ${buildError}`);
                    }
                } else {
                    console.error(`❌ REFRESH FAILED OR STILL NOT ENOUGH MOVES: ${fetchError}`);
                    setError(`Move data not available yet (commentary ahead of API)`);
                }
            };
            
            refreshMoves();
            return; // Don't continue with stale data
        }
        
        // Normal update with existing data - only if commentary is for a different move
        if (gameMoveListRef.current.length > 0 && currentMoveNumber > 0 && currentMoveNumber !== lastProcessedMove) {
            console.log(`🔄 UPDATING to commentary move ${currentMoveNumber}`);
            
            const { game: newGame, moveHistory: newMoveHistory, lastMoveSquares: moveSquares, success, error: buildError } = buildGameIncrementally(currentMoveNumber);
            
            if (success) {
                console.log(`📍 Setting new position: ${newGame.fen()}`);
                setGame(newGame);
                setBoardPosition(newGame.fen());
                setMoveHistory(newMoveHistory);
                setLastMoveSquares(moveSquares);
                setLastProcessedMove(currentMoveNumber);
                setError(null);
                
                console.log(`✅ BOARD UPDATED FOR COMMENTARY`);
                console.log(`   - New FEN: ${newGame.fen()}`);
                console.log(`   - Move History Length: ${newMoveHistory.length}`);
            } else {
                console.error(`❌ FAILED TO BUILD POSITION: ${buildError}`);
                setError(`Failed to build position: ${buildError}`);
            }
        } else {
            console.log(`⏸️ No board update needed - same move or invalid data`);
        }
    }, [currentCommentary]); // Only depend on currentCommentary

    /**
     * Reset board when game changes
     */
    useEffect(() => {
        if (gameId !== lastFetchedGameRef.current) {
            console.log('Resetting board for new game');
            initialSetupRef.current = false;
            setIsInitialized(false);
            setGame(new Chess());
            setBoardPosition('start');
            setLastProcessedMove(0);
            setMoveHistory([]);
            setLastMoveSquares({ from: null, to: null });
            setError(null);
            gameMoveListRef.current = [];
            lastFetchedGameRef.current = null;
        }
    }, [gameId]);

    if (!isInitialized) {
        // Show loading state but also try to show a basic board if we have the data
        if (gameId && username) {
            return (
                <div className="chess-board-container">
                    <div className="mb-6">
                        <h3 className="text-xl font-semibold text-white mb-3">
                            Game Position
                        </h3>
                        <div className="flex justify-between text-sm text-gray-300 mb-4">
                            <span>Loading live position...</span>
                            <span>Following: {username}</span>
                        </div>
                    </div>
                    
                    <div className="chess-board-wrapper mb-6 flex justify-center">
                        <div className="bg-white/10 p-4 rounded-xl backdrop-blur-sm">
                            <Chessboard
                                position="start"
                                boardOrientation="white"
                                arePiecesDraggable={false}
                                boardWidth={500}
                                customBoardStyle={{
                                    borderRadius: '12px',
                                    boxShadow: '0 8px 32px rgba(0, 0, 0, 0.3)'
                                }}
                                customDarkSquareStyle={{ backgroundColor: '#4a5568' }}
                                customLightSquareStyle={{ backgroundColor: '#e2e8f0' }}
                            />
                        </div>
                    </div>
                    
                    <div className="text-center text-gray-400">
                        <p>Loading live game position...</p>
                        <p className="text-xs mt-2">Board will update automatically when ready</p>
                    </div>
                </div>
            );
        }
        
        return (
            <div className="chess-board-container bg-gray-100 rounded-lg p-6 text-center">
                <div className="text-gray-600 mb-4">
                    <div className="w-16 h-16 mx-auto mb-4 bg-gray-300 rounded-lg flex items-center justify-center">
                        <span className="text-2xl">♔</span>
                    </div>
                    <p>Waiting for game to start...</p>
                    {username && (
                        <p className="text-sm text-gray-500 mt-2">
                            Following: {username}
                        </p>
                    )}
                </div>
            </div>
        );
    }

    return (
        <div className="chess-board-container">
            <div className="mb-6">
                <h3 className="text-xl font-semibold text-white mb-3">
                    Game Position
                </h3>
                <div className="flex justify-between text-sm text-gray-300 mb-4">
                    <span>Move: {Math.ceil(lastProcessedMove / 2)}/{Math.ceil(gameMoveListRef.current.length / 2)}</span>
                    <span>Following: {username} ({playerColor})</span>
                </div>
                {error && (
                    <div className="text-xs text-red-400 mb-4 p-3 bg-red-500/20 rounded-lg border border-red-500/30">
                        {error}
                    </div>
                )}
            </div>
            
            <div className="chess-board-wrapper mb-6 flex justify-center">
                <div className="bg-white/10 p-4 rounded-xl backdrop-blur-sm">
                    <Chessboard
                        position={boardPosition}
                        boardOrientation={playerColor}
                        arePiecesDraggable={false}
                        boardWidth={500}
                        customBoardStyle={{
                            borderRadius: '12px',
                            boxShadow: '0 8px 32px rgba(0, 0, 0, 0.3)'
                        }}
                        customDarkSquareStyle={{ backgroundColor: '#4a5568' }}
                        customLightSquareStyle={{ backgroundColor: '#e2e8f0' }}
                        customSquareStyles={{
                            ...(lastMoveSquares.from && {
                                [lastMoveSquares.from]: {
                                    backgroundColor: 'rgba(255, 255, 0, 0.88)',
                                    boxShadow: 'inset 0 0 0 2px rgba(255, 255, 0, 0.8)'
                                }
                            }),
                            ...(lastMoveSquares.to && {
                                [lastMoveSquares.to]: {
                                    backgroundColor: 'rgba(236, 236, 3, 0.93)',
                                    boxShadow: 'inset 0 0 0 2px rgba(255, 255, 0, 0.8)'
                                }
                            })
                        }}
                        animationDuration={300}
                    />
                </div>
            </div>
            
            {currentCommentary && (
                <div className="mb-6 p-4 bg-white/5 rounded-lg border border-white/10">
                    <div className="text-sm text-gray-300 mb-2">
                        <strong className="text-white">Latest Move:</strong> {currentCommentary.latestMove}
                    </div>
                    <div className="text-xs text-gray-400 mb-2">
                        Showing position after move {Math.ceil(currentCommentary.moveNumber / 2)} (half-move {currentCommentary.moveNumber})
                    </div>
                    <div className="text-xs text-blue-400 bg-blue-500/10 p-2 rounded mt-2">
                        <strong>DEBUG:</strong> Board FEN: {boardPosition.substring(0, 20)}...
                        <br />
                        <strong>Last Processed:</strong> {lastProcessedMove}
                        <br />
                        <strong>Commentary Move:</strong> {currentCommentary.moveNumber}
                    </div>
                </div>
            )}
            
            {moveHistory.length > 0 && (
                <div className="bg-white/5 rounded-lg p-4 border border-white/10">
                    <h4 className="text-sm font-medium text-white mb-3">
                        Move History ({Math.ceil(gameMoveListRef.current.length / 2)} moves)
                    </h4>
                    <div className="max-h-40 overflow-y-auto text-xs text-gray-300 bg-black/20 p-3 rounded-lg">
                        {moveHistory.map((move, index) => (
                            <span key={index} className="mr-3 inline-block">
                                {index % 2 === 0 && (
                                    <span className="text-gray-400 mr-1">
                                        {Math.ceil((index + 1) / 2)}.
                                    </span>
                                )}
                                <span className="text-white font-mono">{move.move}</span>
                            </span>
                        ))}
                    </div>
                </div>
            )}
        </div>
    );
}

export default CommentaryChessBoard;