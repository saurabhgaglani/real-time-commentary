# Quick Testing Guide - Audio Playback

This guide will help you test if audio files play in the UI without running the full pipeline.

## Prerequisites

- Audio files exist in the `audio/` folder (generated from previous runs)
- Frontend and backend are ready to run

## Step-by-Step Testing

### Step 1: Start the Frontend
Open Terminal 1:
```bash
npm run dev
```

The frontend should start on `http://localhost:5173`

### Step 2: Start the Backend API
Open Terminal 2:
```bash
uvicorn backend.main:app --reload --port 8000
```

Wait for the logs to show:
```
INFO:     Starting application...
INFO:     Kafka-WebSocket bridge started successfully
```

### Step 3: Open the UI and Connect
1. Open browser to `http://localhost:5173`
2. Enter any username (e.g., "testuser")
3. Click "Analyze" (this will fail but that's ok)
4. Click "Start Live Game"
5. When prompted for game status, it will fail - that's expected

**Alternative:** Manually set a test game_id in the browser console:
```javascript
// Open browser console (F12) and run:
window.testGameId = "test_game_123"
```

### Step 4: Run the Test Audio Producer
Open Terminal 3:
```bash
python backend/test_audio_producer.py
```

The script will:
1. List all audio files found in `audio/` folder
2. Ask for a game_id (use `test_game_123` or whatever you set in the UI)
3. Send fake audio events to Kafka for each audio file

### Step 5: Watch the UI
The audio should start playing automatically in the UI!

You should see:
- Connection status: "Connected" (green)
- Commentary text appearing
- "Playing..." indicator with 🔊 icon
- Queue count if multiple files

## Troubleshooting

### No audio plays

**Check 1: WebSocket Connection**
- Browser console (F12) should show: `"WebSocket connected for game: test_game_123"`
- If not connected, check backend logs for errors

**Check 2: Backend Logs**
Look for these messages:
```
INFO:     Received commentary_audio event for game test_game_123
INFO:     Processing audio event for game test_game_123, move 1, audio: /audio/...
INFO:     Sending audio event to 1 client(s) for game test_game_123, move 1
```

**Check 3: Browser Console**
Should show:
```
Received audio event: {event: 'commentary_audio', game_id: 'test_game_123', ...}
```

**Check 4: Audio Files Accessible**
Open in browser: `http://127.0.0.1:8000/audio/` 
You should see a list of audio files.

**Check 5: Game ID Mismatch**
Make sure the game_id in:
- Frontend (check browser console or UI)
- Test producer (what you entered)
- Backend logs (what it's routing to)

All match exactly!

### Audio files not found

If the test script says "No audio files found":
1. Check the `audio/` folder exists
2. Run `consumer_commentary.py` to generate some audio first
3. Or manually place some `.mp3` files in the `audio/` folder

### WebSocket not connecting

1. Make sure backend is running on port 8000
2. Check CORS settings in `backend/main.py`
3. Check browser console for connection errors
4. Try refreshing the page

## Expected Flow

```
Test Producer → Kafka (chess_stream topic)
                  ↓
            Backend Consumer (filters for commentary_audio)
                  ↓
            WebSocket Bridge (routes by game_id)
                  ↓
            Frontend (plays audio sequentially)
```

## Quick Debug Commands

**Check if backend is running:**
```bash
curl http://127.0.0.1:8000/health
```

**Check if audio files are accessible:**
```bash
curl http://127.0.0.1:8000/audio/
```

**Check Kafka messages:**
```bash
python backend/test_kafka_consumer.py
```

## Success Indicators

✅ Frontend shows "Connected" status
✅ Backend logs show "Sending audio event to 1 client(s)"
✅ Browser console shows "Received audio event"
✅ UI displays commentary text
✅ Audio plays through speakers
✅ Queue count updates as audio plays

## Next Steps

Once this works, you can test the full pipeline:
1. Start all 4 services (frontend, backend, consumer_commentary, producer_lichess)
2. Start a real game on Lichess
3. Make moves and watch live commentary!
