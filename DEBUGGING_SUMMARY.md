# WebSocket Audio Delivery - Debugging Summary

## Problem Identified

The audio was being generated and saved to local storage, but not playing in the UI. The root cause was a **game_id mismatch**.

### Root Cause

1. **Frontend** was using a mock game_id: `game_${username}_${Date.now()}`
2. **Backend Producer** (producer_lichess.py) was using the real Lichess game_id from the API
3. **WebSocket Bridge** was routing messages by game_id
4. Since the game_ids didn't match, the frontend never received the audio events

## Solution Implemented

### 1. Added Environment Variables (.env)
```
TOPIC_OUT_AUDIO="commentary_audio"
TOPIC_COMMENTARY_AUDIO="commentary_audio"
```
This ensures both producer and consumer use the same Kafka topic.

### 2. Added Game Status Endpoint (backend/main.py)
```python
@app.get("/game/status/{username}")
def get_game_status(username: str):
```
This endpoint checks Lichess API to get the real game_id for a user.

### 3. Updated Frontend (frontend/src/App.jsx)
Changed `startLiveGame()` to fetch the real game_id from the backend instead of generating a mock one.

### 4. Enhanced Logging
Added detailed logging throughout the WebSocket bridge to help debug:
- Kafka consumer startup
- Message reception
- WebSocket connections
- Audio event routing

### 5. Changed Consumer Offset (for testing)
Changed `auto.offset.reset` from `"latest"` to `"earliest"` so the consumer reads all messages from the beginning of the topic (useful for testing).

## Testing Steps

### 1. Restart All Services
```bash
# Terminal 1: Frontend
npm run dev

# Terminal 2: Commentary Consumer
python backend/consumer_commentary.py

# Terminal 3: Lichess Producer
python backend/producer_lichess.py

# Terminal 4: Backend API
uvicorn backend.main:app --reload --port 8000
```

### 2. Test the Flow
1. Start a game on Lichess with the username you're tracking
2. In the UI, click "Analyze" to load the user profile
3. Click "Start Live Game" - this will fetch the real game_id
4. Make moves in the Lichess game
5. Audio should now play in the UI!

### 3. Verify Logs

**Backend logs should show:**
```
INFO:     Starting application...
INFO:     Kafka config path: ...
INFO:     Commentary audio topic: commentary_audio
INFO:     Kafka-WebSocket bridge started successfully
INFO:     Kafka config loaded: ..., group: websocket-commentary-consumer
INFO:     Started consuming from topic: commentary_audio
INFO:     WebSocket connection request for game <game_id>
INFO:     WebSocket connection established for game <game_id>
INFO:     Received message from Kafka topic commentary_audio
INFO:     Processing audio event for game <game_id>, move X, audio: /audio/...
INFO:     Sending audio event to 1 client(s) for game <game_id>, move X
```

**Browser console should show:**
```
WebSocket connected for game: <game_id>
Received audio event: {event: 'commentary_audio', game_id: '...', ...}
```

## Additional Debugging Tools

### Test Kafka Consumer
Run this to verify messages are in Kafka:
```bash
python backend/test_kafka_consumer.py
```

This will show all messages in the `commentary_audio` topic.

## Common Issues

### Issue 1: No messages received
- Check that consumer_commentary.py is running and producing messages
- Verify the topic name matches in both producer and consumer
- Check Kafka broker is running

### Issue 2: WebSocket not connecting
- Verify backend is running on port 8000
- Check browser console for connection errors
- Verify CORS settings allow localhost:5173

### Issue 3: Wrong game_id
- Make sure you click "Start Live Game" AFTER starting a game on Lichess
- Check the backend logs to see what game_id is being used
- Verify the producer is tracking the correct username

### Issue 4: Audio files exist but don't play
- Check browser console for audio loading errors
- Verify audio files are accessible at http://127.0.0.1:8000/audio/
- Check audio file format is supported (MP3 should work)

## Next Steps

For production, consider:
1. Polling the game status endpoint periodically to detect when games start/end
2. Adding a UI indicator showing the current game_id
3. Handling multiple concurrent games
4. Adding reconnection logic if the game_id changes
5. Changing `auto.offset.reset` back to `"latest"` for production
