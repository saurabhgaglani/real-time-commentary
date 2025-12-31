# Comprehensive Logging Added

## What Was Added:

### Startup Logs (All Services)
Every service now logs on startup:
```
============================================================
[SERVICE NAME] SERVICE STARTING
============================================================
[STARTUP] PID: 12345
[STARTUP] Script: backend/[script_name].py
[STARTUP] Time: 2025-12-31 04:30:00 UTC
[CONFIG] Kafka config path: /secrets/client.properties
[CONFIG] Config exists: True
[KAFKA] Successfully loaded config with 7 entries
[KAFKA] Bootstrap servers: pkc-619z3.us-east1.gcp.confluent.cloud:9092
```

### Kafka Stream Status
Clear indication when Kafka is UP:
```
[KAFKA] ✓ Consumer created successfully
[KAFKA] ✓ Subscribed to topics: chess_stream
[KAFKA] ✓ Producer created successfully
[KAFKA] Kafka stream is UP and RUNNING
```

### Heartbeat Logs
Services log every 60 seconds to show they're alive:
```
[KAFKA] Still polling (count: 120)... Kafka stream active
```

### Shutdown Logs
When services stop (gracefully or crash):
```
[SHUTDOWN] Received interrupt signal
[SHUTDOWN] Consumer service stopped at 2025-12-31 05:00:00 UTC
[CLEANUP] Closing consumer...
[CLEANUP] Consumer closed
```

Or if crashed:
```
[FATAL] Consumer crashed: [error message]
[stack trace]
```

### Process Lifecycle Tracking

#### Producer Logs:
```
============================================================
PRODUCER SERVICE STARTING
============================================================
[STARTUP] PID: 123
[STARTUP] Script: backend/producer_lichess.py
[STARTUP] Time: 2025-12-31 04:30:00 UTC
[KAFKA] ✓ Consumer created successfully
[KAFKA] ✓ Subscribed to topic: chess_stream
[KAFKA] Kafka stream is UP and RUNNING
[WAIT] Waiting for profile message from UI...
[KAFKA] Still polling (count: 30)... Kafka stream active
[PROFILE_RECEIVED] ✓ username=player123 (age: 2.5s)
[KAFKA] Consumer closed after receiving profile
[TRACKING] Starting game tracking for: player123
[PRODUCER] ✓ Kafka producer created
[START] ✓ Tracking user=player123
[SESSION_START] ✓ abc123xyz
[PROFILE_EMITTED] ✓ game_id=abc123xyz
[MOVE] ✓ abc123xyz #1 e4
[MOVE] ✓ abc123xyz #2 e5
[TRACKING] Still tracking player123 (loop: 60)...
[SESSION_END] ✓ abc123xyz
[SHUTDOWN] Tracking interrupted for player123
[SHUTDOWN] Producer service stopped at 2025-12-31 05:00:00 UTC
```

#### Consumer Logs:
```
============================================================
CONSUMER SERVICE STARTING
============================================================
[STARTUP] PID: 456
[STARTUP] Script: backend/consumer_commentary.py
[STARTUP] Time: 2025-12-31 04:30:00 UTC
[CONFIG] Consumer group: commentary-consumer-group-1
[CONFIG] Auto offset reset: latest
[KAFKA] ✓ Consumer created successfully
[KAFKA] ✓ Subscribed to topics: chess_stream
[KAFKA] ✓ Producer created successfully
[KAFKA] Kafka stream is UP and RUNNING
[BOOT] ✓ consuming: chess_stream | producing: chess_stream
============================================================
[KAFKA] Still polling (count: 60)... Kafka stream active
[PROFILE] ✓ cached game_id=abc123xyz
[SESSION] session_start game_id=abc123xyz user=player123
[MOVE] game_id=abc123xyz #1 Latest Move=e4 player colour=White
[PROMPT] Building prompt for move 1...
[LLM] Calling LLM - FIRST COMMENTARY
[LLM] ✓ Response received: A bold opening move from White...
[TTS] Generating audio...
[TTS] ✓ Audio generated: /audio/Tue_Dec_31_043015_2025.mp3
[AUDIO] ✓ emitted game_id=abc123xyz move=1
[MOVE] game_id=abc123xyz #2 Latest Move=e5 player colour=Black
[PROMPT] Building prompt for move 2...
[LLM] Calling LLM - MOVE COMMENTARY
[LLM] ✓ Response received: Black responds symmetrically...
[TTS] Generating audio...
[TTS] ✓ Audio generated: /audio/Tue_Dec_31_043020_2025.mp3
[AUDIO] ✓ emitted game_id=abc123xyz move=2
[SHUTDOWN] Received interrupt signal
[SHUTDOWN] Consumer service stopped at 2025-12-31 05:00:00 UTC
[CLEANUP] Closing consumer...
[CLEANUP] Consumer closed
```

## How to View Logs:

### View Recent Logs:
```bash
# Producer
gcloud run services logs read chess-commentary-producer --region=us-central1 --project=chess-commentary-2026 --limit=100

# Consumer
gcloud run services logs read chess-commentary-consumer --region=us-central1 --project=chess-commentary-2026 --limit=100

# Backend
gcloud run services logs read chess-commentary-backend --region=us-central1 --project=chess-commentary-2026 --limit=100
```

### Stream Live Logs:
```bash
# Producer
gcloud run services logs tail chess-commentary-producer --region=us-central1 --project=chess-commentary-2026

# Consumer
gcloud run services logs tail chess-commentary-consumer --region=us-central1 --project=chess-commentary-2026
```

### Search for Specific Events:
```bash
# Find when Kafka stream started
gcloud run services logs read chess-commentary-consumer --region=us-central1 --project=chess-commentary-2026 --limit=200 | grep "Kafka stream is UP"

# Find shutdowns/crashes
gcloud run services logs read chess-commentary-consumer --region=us-central1 --project=chess-commentary-2026 --limit=200 | grep -E "SHUTDOWN|FATAL"

# Find profile received
gcloud run services logs read chess-commentary-producer --region=us-central1 --project=chess-commentary-2026 --limit=200 | grep "PROFILE_RECEIVED"

# Find commentary generation
gcloud run services logs read chess-commentary-consumer --region=us-central1 --project=chess-commentary-2026 --limit=200 | grep "AUDIO.*emitted"
```

## What You Can Now Debug:

### 1. Service Lifecycle
- ✅ When service started (PID, timestamp)
- ✅ Which script is running
- ✅ When service stopped (graceful or crash)
- ✅ Why service crashed (error message + stack trace)

### 2. Kafka Connection
- ✅ When Kafka stream is UP
- ✅ Which topics are subscribed
- ✅ Bootstrap servers being used
- ✅ Consumer group names
- ✅ Heartbeat every 60 seconds

### 3. Message Flow
- ✅ Profile received by producer
- ✅ Profile cached by consumer
- ✅ Moves published by producer
- ✅ Moves received by consumer
- ✅ Commentary generated
- ✅ Audio emitted

### 4. Timing Issues
- ✅ Profile age when received (e.g., "age: 2.5s")
- ✅ Polling activity (count every 60s)
- ✅ Cooldown skips
- ✅ Duplicate move skips

### 5. Cloud Run Issues
- ✅ Service restarts (new PID in logs)
- ✅ Health check failures (no heartbeat logs)
- ✅ Memory/CPU issues (crash logs)
- ✅ Secret mounting issues (config load errors)

## Log Markers to Watch For:

### Good Signs:
- `✓` checkmarks indicate success
- `Kafka stream is UP and RUNNING`
- `Still polling... Kafka stream active`
- `PROFILE_RECEIVED`
- `AUDIO ✓ emitted`

### Warning Signs:
- `[SKIP]` - Message filtered or ignored
- `[COOLDOWN]` - Too soon after last commentary
- `[NO_PROFILE]` - Move received but no profile cached

### Error Signs:
- `[KAFKA_ERROR]` - Kafka connection issue
- `[FATAL]` - Service crashed
- `[ERROR]` - Non-fatal error
- No heartbeat logs for >2 minutes - service may be dead

## Deploy to Get New Logs:

```bash
gcloud builds submit --config=cloudbuild.yaml --project=chess-commentary-2026
```

After deployment, you'll see comprehensive logs for debugging!
