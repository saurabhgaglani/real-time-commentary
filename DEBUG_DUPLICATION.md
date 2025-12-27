# Debugging Audio Duplication Issue

Audio is generated once but played twice on the UI. Let's identify where the duplication happens.

## Step 1: Check Multiple Backend Instances

**Windows:**
```bash
tasklist | findstr "python"
```

**Look for:** Multiple `python.exe` processes running `uvicorn`

**Expected:** Only ONE uvicorn process

**If multiple found:** Kill all and restart only one:
```bash
taskkill /F /IM python.exe
# Then restart only one backend
uvicorn backend.main:app --reload --port 8000
```

## Step 2: Check Backend Logs

When audio is generated, look for these logs:

```
INFO: Received commentary_audio event for game <game_id>
INFO: Processing audio event for game <game_id>, move X, audio: /audio/...
INFO: Sending audio event to Y client(s) for game <game_id>, move X
```

**Questions:**
1. Do you see "Processing audio event" **once or twice** for the same move?
2. How many clients does it say? (Should be 1)
3. Do you see "Skipping duplicate audio event" logs?

## Step 3: Check Browser Console

Open browser console (F12) and look for:

```
Received audio event: {event: 'commentary_audio', game_id: '...', move_number: X, ...}
```

**Questions:**
1. Do you see this log **once or twice** for the same move?
2. Are the `created_at_ms` timestamps identical?

## Step 4: Check WebSocket Connections

In browser console, run:
```javascript
// Check how many WebSocket connections exist
console.log('WebSocket readyState:', window.performance.getEntriesByType('resource').filter(r => r.name.includes('ws://')))
```

**Expected:** Only 1 WebSocket connection

## Step 5: Check Frontend Re-renders

The `useCommentary` hook might be mounting twice (React StrictMode issue).

**Check `frontend/src/main.jsx` or `frontend/src/index.jsx`:**

Look for:
```jsx
<React.StrictMode>
  <App />
</React.StrictMode>
```

**If found:** StrictMode causes double mounting in development. Try removing it temporarily:
```jsx
<App />
```

## Step 6: Add Deduplication Logs

Add this to `backend/websocket_manager.py` in `process_audio_event`:

```python
# After creating event_id
logger.info(f"[DEDUP CHECK] Event ID: {event_id}")

# After checking if in processed_events
if event_id in self.processed_events:
    logger.warning(f"[DUPLICATE DETECTED] Skipping duplicate: {event_id}")
    return
else:
    logger.info(f"[NEW EVENT] Processing: {event_id}")
```

Restart backend and check if you see `[DUPLICATE DETECTED]` logs.

## Step 7: Check Kafka Consumer Group

Run this to see consumer group status:
```bash
python backend/test_kafka_consumer.py
```

Let it run and see if the same audio event appears twice in the output.

## Common Causes Summary

| Cause | Symptom | Fix |
|-------|---------|-----|
| Multiple backends | Backend logs show processing twice | Kill extra processes |
| Multiple WebSocket connections | Browser shows 2+ connections | Check for duplicate `connect()` calls |
| React StrictMode | Frontend mounts twice | Remove `<React.StrictMode>` |
| Deduplication not working | No "Skipping duplicate" logs | Check `created_at_ms` is present |
| Multiple browser tabs | Multiple clients connected | Close extra tabs |

## Report Back

Please check:
1. ✅ How many python/uvicorn processes are running?
2. ✅ Backend logs - does "Processing audio event" appear once or twice?
3. ✅ Browser console - does "Received audio event" appear once or twice?
4. ✅ Are you using React StrictMode?
5. ✅ How many browser tabs/windows have the app open?
