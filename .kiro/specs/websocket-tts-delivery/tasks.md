# Implementation Plan

- [x] 1. Set up WebSocket infrastructure in backend





  - Create `backend/websocket_manager.py` with ConnectionManager class
  - Implement connection lifecycle methods (connect, disconnect, send_audio_event)
  - Add WebSocket endpoint `/ws/commentary/{game_id}` to `backend/main.py`
  - _Requirements: 1.1, 1.2, 1.4, 1.5_

- [x] 2. Implement Kafka-to-WebSocket bridge





  - Create KafkaWebSocketBridge class in `backend/websocket_manager.py`
  - Implement background task to consume from `commentary_audio` topic
  - Add message routing logic to send events to correct game_id connections
  - Handle Kafka consumer errors gracefully without crashing
  - _Requirements: 2.1, 2.2, 2.3, 2.4, 2.5, 5.2_

- [x] 3. Add static audio file serving












  - Mount `/audio` static files directory in `backend/main.py`
  - Verify CORS configuration allows frontend access
  - Test 404 handling for missing audio files
  - _Requirements: 4.1, 4.2, 4.3, 4.4, 4.5_

- [x] 4. Create frontend audio queue manager







  - Create `frontend/src/utils/audioQueue.js` with AudioQueueManager class
  - Implement enqueue, playNext, and playAudio methods
  - Add error handling for audio load and playback failures
  - Implement clear queue functionality
  - _Requirements: 3.1, 3.2, 3.3, 3.4, 3.5, 5.3_

- [x] 5. Build WebSocket client hook







  - Create `frontend/src/hooks/useCommentary.js` custom hook
  - Implement WebSocket connection with reconnection logic
  - Integrate AudioQueueManager for playback
  - Manage connection state and error handling
  - Add exponential backoff for reconnection attempts
  - _Requirements: 1.1, 1.3, 1.4, 5.1, 5.4_

- [x] 6. Create commentary player UI component







  - Create `frontend/src/components/CommentaryPlayer.jsx`
  - Display connection status indicator
  - Show current commentary text and move information
  - Display queue length when audio is queued
  - Show error messages when they occur
  - _Requirements: 6.1, 6.2, 6.3, 6.4, 6.5_
-

- [x] 7. Integrate commentary player into main app






  - Update `frontend/src/App.jsx` to include CommentaryPlayer component
  - Pass game_id to CommentaryPlayer when game starts
  - Handle game session lifecycle (start/stop commentary)
  - _Requirements: 1.1, 6.1_
-

- [x] 8. Add backend startup integration






  - Start KafkaWebSocketBridge background task on FastAPI startup
  - Add graceful shutdown for Kafka consumer
  - Add logging for WebSocket connections and audio events
  - _Requirements: 2.1, 5.2_

- [ ]* 9. Add error monitoring and logging
  - Add structured logging for WebSocket events
  - Log audio playback failures on frontend
  - Add console warnings for reconnection attempts
  - _Requirements: 5.1, 5.2, 5.3_

- [ ]* 10. Performance optimization
  - Implement audio preloading for next item in queue
  - Add queue size limit (max 10 items) to prevent memory issues
  - Clear old Audio objects after playback completion
  - _Requirements: 3.1, 3.2, 3.3_
