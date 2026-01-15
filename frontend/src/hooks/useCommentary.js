import { useState, useEffect, useRef, useCallback } from 'react';
import AudioQueueManager from '../utils/audioQueue.js';
import API_CONFIG from '../config/environment.js';

/**
 * Custom hook for managing live commentary WebSocket connection
 * 
 * Handles WebSocket lifecycle, reconnection with exponential backoff,
 * audio queue management, and state updates.
 * 
 * @param {string} gameId - The lichess game ID to subscribe to
 * @returns {Object} Commentary state and controls
 */
function useCommentary(gameId) {
    // Connection state
    const [isConnected, setIsConnected] = useState(false);
    const [connectionStatus, setConnectionStatus] = useState('disconnected');
    const [error, setError] = useState(null);

    // Commentary state
    const [currentCommentary, setCurrentCommentary] = useState(null);
    const [queueLength, setQueueLength] = useState(0);

    // Refs for WebSocket and audio manager (persist across renders)
    const wsRef = useRef(null);
    const audioManagerRef = useRef(null);
    const reconnectTimeoutRef = useRef(null);
    const reconnectAttemptsRef = useRef(0);
    const shouldReconnectRef = useRef(true);

    // Reconnection configuration
    const INITIAL_RECONNECT_DELAY = 1000; // 1 second
    const MAX_RECONNECT_DELAY = 30000; // 30 seconds
    const RECONNECT_MULTIPLIER = 2;

    /**
     * Calculate exponential backoff delay for reconnection
     */
    const getReconnectDelay = useCallback(() => {
        const delay = Math.min(
            INITIAL_RECONNECT_DELAY * Math.pow(RECONNECT_MULTIPLIER, reconnectAttemptsRef.current),
            MAX_RECONNECT_DELAY
        );
        return delay;
    }, []);

    /**
     * Initialize audio queue manager
     */
    useEffect(() => {
        if (!audioManagerRef.current) {
            const audioManager = new AudioQueueManager();
            
            // Set up state change callback
            audioManager.onStateChange = (state) => {
                setQueueLength(state.queueLength);
                
                if (state.currentEvent) {
                    setCurrentCommentary({
                        text: state.currentEvent.commentary_text,
                        moveNumber: state.currentEvent.move_number,
                        latestMove: state.currentEvent.latest_move,
                        isPlaying: state.isPlaying
                    });
                } else if (!state.isPlaying) {
                    setCurrentCommentary(null);
                }
            };
            
            audioManagerRef.current = audioManager;
        }

        return () => {
            // Cleanup audio manager on unmount
            if (audioManagerRef.current) {
                audioManagerRef.current.clear();
            }
        };
    }, []);

    /**
     * Connect to WebSocket server
     */
    const connect = useCallback(() => {
        if (!gameId) {
            setError('No game ID provided');
            return;
        }

        // Don't create new connection if already connected
        if (wsRef.current?.readyState === WebSocket.OPEN) {
            return;
        }

        // Clear any pending reconnection attempts
        if (reconnectTimeoutRef.current) {
            clearTimeout(reconnectTimeoutRef.current);
            reconnectTimeoutRef.current = null;
        }

        setConnectionStatus('connecting');
        setError(null);

        try {
            const ws = new WebSocket(`${API_CONFIG.WS_URL}${API_CONFIG.ENDPOINTS.WS_COMMENTARY}/${gameId}`);
            wsRef.current = ws;

            ws.onopen = () => {
                console.log('WebSocket connected for game:', gameId);
                setIsConnected(true);
                setConnectionStatus('connected');
                setError(null);
                reconnectAttemptsRef.current = 0; // Reset reconnect attempts on successful connection
            };

            ws.onmessage = (event) => {
                try {
                    const data = JSON.parse(event.data);
                    
                    // Handle commentary audio events
                    if (data.event === 'commentary_audio') {
                        console.log('Received audio event:', data);
                        
                        // Add to audio queue
                        if (audioManagerRef.current) {
                            audioManagerRef.current.enqueue(data);
                        }
                    }
                } catch (parseError) {
                    console.error('Failed to parse WebSocket message:', parseError);
                    setError('Failed to parse server message');
                }
            };

            ws.onerror = (errorEvent) => {
                console.error('WebSocket error:', errorEvent);
                setError('Connection error occurred');
            };

            ws.onclose = (closeEvent) => {
                console.log('WebSocket closed:', closeEvent.code, closeEvent.reason);
                setIsConnected(false);
                setConnectionStatus('disconnected');
                wsRef.current = null;

                // Attempt reconnection if enabled
                if (shouldReconnectRef.current) {
                    const delay = getReconnectDelay();
                    console.log(`Reconnecting in ${delay}ms (attempt ${reconnectAttemptsRef.current + 1})`);
                    
                    setConnectionStatus('reconnecting');
                    reconnectAttemptsRef.current += 1;
                    
                    reconnectTimeoutRef.current = setTimeout(() => {
                        connect();
                    }, delay);
                }
            };
        } catch (connectionError) {
            console.error('Failed to create WebSocket:', connectionError);
            setError('Failed to establish connection');
            setConnectionStatus('error');
        }
    }, [gameId, getReconnectDelay]);

    /**
     * Disconnect from WebSocket server
     */
    const disconnect = useCallback(() => {
        shouldReconnectRef.current = false;
        
        // Clear any pending reconnection
        if (reconnectTimeoutRef.current) {
            clearTimeout(reconnectTimeoutRef.current);
            reconnectTimeoutRef.current = null;
        }

        // Close WebSocket connection
        if (wsRef.current) {
            wsRef.current.close();
            wsRef.current = null;
        }

        // Clear audio queue
        if (audioManagerRef.current) {
            audioManagerRef.current.clear();
        }

        setIsConnected(false);
        setConnectionStatus('disconnected');
        setCurrentCommentary(null);
        setQueueLength(0);
        reconnectAttemptsRef.current = 0;
    }, []);

    /**
     * Clear audio queue without disconnecting
     */
    const clearQueue = useCallback(() => {
        if (audioManagerRef.current) {
            audioManagerRef.current.clear();
        }
        setCurrentCommentary(null);
        setQueueLength(0);
    }, []);

    /**
     * Auto-connect when gameId changes
     */
    useEffect(() => {
        if (gameId) {
            shouldReconnectRef.current = true;
            connect();
        }

        // Cleanup on unmount or gameId change
        return () => {
            shouldReconnectRef.current = false;
            
            if (reconnectTimeoutRef.current) {
                clearTimeout(reconnectTimeoutRef.current);
            }
            
            if (wsRef.current) {
                wsRef.current.close();
            }
            
            if (audioManagerRef.current) {
                audioManagerRef.current.clear();
            }
        };
    }, [gameId, connect]);

    return {
        // Connection state
        isConnected,
        connectionStatus,
        
        // Commentary state
        currentCommentary,
        queueLength,
        
        // Error state
        error,
        
        // Controls
        connect,
        disconnect,
        clearQueue
    };
}

export default useCommentary;
