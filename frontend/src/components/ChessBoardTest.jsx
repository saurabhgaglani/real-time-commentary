import React, { useState } from 'react';
import CommentaryChessBoard from './CommentaryChessBoard.jsx';

/**
 * Test component for the CommentaryChessBoard
 * Simulates commentary events to test board functionality
 */
function ChessBoardTest() {
    const [testCommentary, setTestCommentary] = useState(null);
    const [moveNumber, setMoveNumber] = useState(1);

    const testMoves = [
        { move: 'e4', commentary: 'White opens with the king\'s pawn, a classical choice.' },
        { move: 'e5', commentary: 'Black responds symmetrically in the center.' },
        { move: 'Nf3', commentary: 'The knight develops, attacking the e5 pawn.' },
        { move: 'Nc6', commentary: 'Black defends and develops simultaneously.' },
        { move: 'Bb5', commentary: 'The Spanish Opening - a timeless weapon.' }
    ];

    const simulateCommentary = (moveNum) => {
        if (moveNum <= testMoves.length) {
            const move = testMoves[moveNum - 1];
            setTestCommentary({
                moveNumber: moveNum,
                latestMove: move.move,
                text: move.commentary,
                isPlaying: false
            });
            setMoveNumber(moveNum);
        }
    };

    const resetBoard = () => {
        setTestCommentary(null);
        setMoveNumber(1);
    };

    return (
        <div className="chess-board-test p-6 bg-gray-100 min-h-screen">
            <div className="max-w-4xl mx-auto">
                <h1 className="text-2xl font-bold mb-6">Chess Board Test</h1>
                
                <div className="mb-6 flex gap-2 flex-wrap">
                    <button 
                        onClick={() => simulateCommentary(1)}
                        className="px-4 py-2 bg-blue-500 text-white rounded hover:bg-blue-600"
                    >
                        Start Game (e4)
                    </button>
                    {[2, 3, 4, 5].map(num => (
                        <button 
                            key={num}
                            onClick={() => simulateCommentary(num)}
                            className="px-4 py-2 bg-green-500 text-white rounded hover:bg-green-600"
                            disabled={!testCommentary}
                        >
                            Move {num}
                        </button>
                    ))}
                    <button 
                        onClick={resetBoard}
                        className="px-4 py-2 bg-red-500 text-white rounded hover:bg-red-600"
                    >
                        Reset
                    </button>
                </div>

                <div className="bg-white p-4 rounded-lg shadow">
                    <CommentaryChessBoard 
                        currentCommentary={testCommentary}
                        gameId="test-game-123"
                        username="test-user"
                    />
                </div>

                {testCommentary && (
                    <div className="mt-4 p-4 bg-gray-800 text-white rounded-lg">
                        <h3 className="font-bold mb-2">Current Commentary:</h3>
                        <p className="text-sm text-gray-300">Move {testCommentary.moveNumber}: {testCommentary.latestMove}</p>
                        <p>{testCommentary.text}</p>
                    </div>
                )}
            </div>
        </div>
    );
}

export default ChessBoardTest;