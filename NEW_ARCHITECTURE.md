# New Architecture - HTTP-Triggered Producer

## Problem with Old Architecture

The old architecture had a timing issue:
- Producer waited for Kafka messages using a consumer group
- If producer started before you clicked "Analyze", it would miss the message
- Using `earliest` offset would process old profiles from previous sessions
- Using timestamp-based consumer groups caused restarts to miss messages

## New Architecture

### Flow:

```
User clicks "Analyze" 
    ↓
Backend (main.py)
    ├─→ Publishes profile to Kafka (for consumer)
    └─→ HTTP POST to Producer /start-tracking
            ↓
        Producer Service
            ├─→ Starts tracking thread for this user
            ├─→ Polls Lichess for game status
            ├─→ Publishes moves to Kafka
            └─→ Consumer generates commentary
```

### Key Changes:

1. **Producer is now an HTTP service** (Flask app on port 8080)
   - Endpoint: `POST /start-tracking` with `{username, profile}`
   - Health endpoint: `GET /health`
   - Can handle multiple users concurrently

2. **Backend triggers producer directly**
   - After publishing to Kafka, backend calls producer HTTP endpoint
   - No timing issues - producer starts immediately when you click Analyze
   - Falls back gracefully if producer is unreachable

3. **Producer still listens to Kafka** (legacy support)
   - Runs Kafka listener in background thread
   - Filters out old messages (>5 minutes)
   - Prevents duplicate tracking of same user

4. **Thread-based tracking**
   - Each user gets their own tracking thread
   - Threads are cleaned up when games end
   - Multiple users can be tracked simultaneously

## Files Modified:

### backend/main.py
- Added HTTP call to producer service in `/analyze` endpoint
- Sets `PRODUCER_SERVICE_URL` environment variable
- Gracefully handles producer service being unavailable

### backend/producer_lichess.py
- Complete rewrite to Flask-based HTTP service
- Added `/start-tracking` endpoint
- Added background Kafka listener (legacy support)
- Thread-based tracking for multiple users
- Automatic cleanup of completed tracking threads

### new_requirements.txt
- Added `Flask==3.1.0` for HTTP server

### cloudbuild.yaml
- Producer now allows unauthenticated requests (for backend to call it)
- Backend has `PRODUCER_SERVICE_URL` environment variable
- Producer has higher concurrency (10 instead of 1)
- Removed `--no-traffic` from producer (needs to receive HTTP requests)

## Benefits:

✅ **No timing issues** - Producer starts exactly when you click Analyze
✅ **No old profiles** - Only tracks users you explicitly analyze
✅ **Multiple users** - Can track multiple games simultaneously
✅ **Self-contained** - No manual service management needed
✅ **Resilient** - Falls back to Kafka if HTTP fails
✅ **Clean architecture** - Clear separation of concerns

## Deployment:

```bash
gcloud builds submit --config=cloudbuild.yaml --project=chess-commentary-2026
```

## Testing After Deployment:

1. **Check producer is running:**
   ```bash
   curl https://chess-commentary-producer-zph6bbw55a-uc.a.run.app/health
   ```
   Should return: `{"status": "ok", "active_trackers": 0}`

2. **Click "Analyze" in UI**

3. **Check backend logs:**
   ```bash
   gcloud run services logs read chess-commentary-backend --region=us-central1 --project=chess-commentary-2026 --limit=20
   ```
   Should see: `[PRODUCER] Successfully triggered tracking for <username>`

4. **Check producer logs:**
   ```bash
   gcloud run services logs read chess-commentary-producer --region=us-central1 --project=chess-commentary-2026 --limit=20
   ```
   Should see:
   - `[HTTP] Started tracking <username>`
   - `[START] Tracking user=<username>`
   - `[SESSION_START] <game_id>` (if in game)
   - `[MOVE] <game_id> #1 e4` (when moves happen)

5. **Check consumer logs:**
   ```bash
   gcloud run services logs read chess-commentary-consumer --region=us-central1 --project=chess-commentary-2026 --limit=20
   ```
   Should see:
   - `[PROFILE] cached game_id=<game_id>`
   - `[MOVE] game_id=<game_id> #1`
   - `CALLING LLM`
   - `[AUDIO] emitted`

## Environment Variables:

### Backend:
- `PRODUCER_SERVICE_URL` - URL of producer service (set in cloudbuild.yaml)

### Producer:
- `KAFKA_CONFIG` - Path to Kafka config
- `TOPIC_PROFILE_IN` - Topic for profile messages
- `TOPIC_LIVE_MOVES` - Topic for move messages
- `TOPIC_SESSION_EVENTS` - Topic for session events
- `POLL_SECONDS` - Polling interval for Lichess API

## API Endpoints:

### Producer Service:

**POST /start-tracking**
```json
Request:
{
  "username": "player_name",
  "profile": { ... }
}

Response:
{
  "status": "tracking_started",
  "username": "player_name"
}
```

**GET /health**
```json
Response:
{
  "status": "ok",
  "active_trackers": 2
}
```

## Troubleshooting:

### Producer not receiving HTTP requests:
- Check if producer service is `--allow-unauthenticated`
- Verify `PRODUCER_SERVICE_URL` in backend environment variables
- Check backend logs for HTTP errors

### Multiple tracking threads for same user:
- Producer checks if user is already being tracked
- Returns `already_tracking` status if duplicate request

### Old profiles being processed:
- Kafka listener filters messages older than 5 minutes
- HTTP endpoint always accepts (assumes it's a fresh request)

## Migration Notes:

- Old Kafka-only approach still works (backward compatible)
- HTTP approach is preferred for new deployments
- Both methods can coexist
- No changes needed to consumer or frontend
