# Final Fixes Summary - Kafka-Only Approach

## What Was Fixed:

### ✅ 1. Secret Mounting (CRITICAL FIX)
**Problem:** client.properties was copied during Docker build but not accessible in Cloud Run.

**Solution:**
- Removed `COPY client.properties` from all Dockerfiles
- Added `/secrets` directory creation
- Mounted secret in cloudbuild.yaml: `/secrets/client.properties=kafka-client-properties:latest`
- Updated `KAFKA_CONFIG` env var to `/secrets/client.properties`

### ✅ 2. Health Check Endpoints (CRITICAL FIX)
**Problem:** Cloud Run expects HTTP services. Consumer/Producer had no HTTP endpoints.

**Solution:**
- Created `backend/health_server.py` - lightweight HTTP server
- Added health server startup to consumer and producer
- Both services now respond to health checks on port 8080

### ✅ 3. Consumer Audio Message Filter (BUG FIX)
**Problem:** Consumer filtered for `audio_base64` but produced `audio_url`, causing it to process its own messages.

**Solution:**
- Updated filter to check for: `event == "commentary_audio"` OR `audio_url` OR `audio_base64`
- Prevents infinite loops and duplicate processing

### ✅ 4. Producer Consumer Group Strategy
**Problem:** Timing issues with profile messages.

**Solution:**
- Uses fixed consumer group: `lichess-profile-consumer-fixed`
- Uses `auto.offset.reset=earliest` to catch recent profiles
- Filters out profiles older than 10 minutes
- This way it can pick up profiles published shortly before it started

### ✅ 5. Increased Consumer Resources
**Problem:** Consumer needs more resources for AI processing.

**Solution:**
- Increased memory from 1Gi to 2Gi
- Increased CPU from 1 to 2 cores

## What Was NOT Changed:

- ❌ No HTTP endpoints for triggering (reverted)
- ❌ No Flask dependency (removed)
- ❌ Pure Kafka-based communication
- ✅ All original Kafka logic intact

## Architecture:

```
User clicks "Analyze"
    ↓
Backend (main.py)
    └─→ Publishes profile to Kafka topic: chess_stream
            ↓
        Producer (producer_lichess.py)
            ├─→ Consumes profile from Kafka
            ├─→ Polls Lichess for game status
            └─→ Publishes moves to Kafka
                    ↓
                Consumer (consumer_commentary.py)
                    ├─→ Consumes profile and moves
                    ├─→ Generates commentary (Gemini AI)
                    ├─→ Generates audio (ElevenLabs TTS)
                    └─→ Publishes audio to Kafka
                            ↓
                        WebSocket Manager (main.py)
                            └─→ Delivers audio to frontend
```

## Files Modified:

1. ✅ `backend/health_server.py` - NEW: Health check HTTP server
2. ✅ `backend/consumer_commentary.py` - Added health server + fixed audio filter
3. ✅ `backend/producer_lichess.py` - Added health server + improved consumer group
4. ✅ `backend/main.py` - No changes (pure Kafka)
5. ✅ `Dockerfile.backend/consumer/producer` - Removed client.properties copy, added /secrets
6. ✅ `cloudbuild.yaml` - Mount secrets, increased consumer resources
7. ✅ `new_requirements.txt` - No Flask (reverted)

## Deploy:

```bash
gcloud builds submit --config=cloudbuild.yaml --project=chess-commentary-2026
```

## Expected Behavior After Deployment:

1. **Producer starts** → Waits for profile messages from Kafka
2. **You click "Analyze"** → Backend publishes profile to Kafka
3. **Producer receives profile** → Starts tracking the game
4. **Producer publishes moves** → Consumer generates commentary
5. **Consumer publishes audio** → WebSocket delivers to frontend

## Key Points:

- Producer uses `earliest` offset with 10-minute filter
- This catches profiles published up to 10 minutes ago
- Prevents processing very old profiles from previous sessions
- Fixed consumer group means it remembers its position
- Health endpoints keep services alive in Cloud Run

## Potential Timing Issue:

If producer starts MORE than 10 minutes after you click "Analyze", it will miss the profile. 

**Workaround:** Just click "Analyze" again to send a fresh profile.

**Why this is acceptable:**
- Producer has `--min-instances=1` so it stays running
- In practice, producer will be running when you click Analyze
- 10-minute window is generous for normal usage
- Simple Kafka-only architecture, no HTTP complexity
