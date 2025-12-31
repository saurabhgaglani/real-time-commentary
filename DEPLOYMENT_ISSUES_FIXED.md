# Google Cloud Deployment Issues - FIXED

## Summary of Problems Found

Your commentary system isn't working on Google Cloud due to **3 critical issues**:

### 🔴 Issue 1: Kafka client.properties Not Accessible (CRITICAL)
**Problem:** Your Dockerfiles copy `client.properties` during build, but in Cloud Run you're storing it as a secret that was never mounted. The containers couldn't read the Kafka configuration.

**Status:** ✅ FIXED
- Updated all Dockerfiles to create `/secrets` directory
- Updated `cloudbuild.yaml` to mount secret: `/secrets/client.properties=kafka-client-properties:latest`
- Updated `KAFKA_CONFIG` env var to point to `/secrets/client.properties`

### 🔴 Issue 2: Consumer/Producer Services Need HTTP Endpoints
**Problem:** Cloud Run expects HTTP services. Your consumer/producer are long-running Kafka consumers without HTTP endpoints, causing Cloud Run to kill them or fail health checks.

**Status:** ✅ FIXED
- Created `backend/health_server.py` - lightweight HTTP server for health checks
- Updated `consumer_commentary.py` to start health server on port 8080
- Updated `producer_lichess.py` to start health server on port 8080
- Added `--min-instances=1` to keep services running

### 🟡 Issue 3: Increased Consumer Resources
**Problem:** Consumer needs more memory/CPU for Gemini AI and ElevenLabs TTS processing.

**Status:** ✅ FIXED
- Increased consumer memory from 1Gi to 2Gi
- Increased consumer CPU from 1 to 2 cores

## Files Modified

### New Files Created:
1. ✅ `backend/health_server.py` - HTTP health check server
2. ✅ `CLOUD_DEPLOYMENT_FIX.md` - Detailed fix guide
3. ✅ `verify-secrets.sh` - Script to verify secrets before deployment
4. ✅ `DEPLOYMENT_ISSUES_FIXED.md` - This file

### Files Updated:
1. ✅ `backend/consumer_commentary.py` - Added health server import and startup
2. ✅ `backend/producer_lichess.py` - Added health server import and startup
3. ✅ `Dockerfile.backend` - Removed client.properties copy, added /secrets directory
4. ✅ `Dockerfile.consumer` - Removed client.properties copy, added /secrets directory
5. ✅ `Dockerfile.producer` - Removed client.properties copy, added /secrets directory
6. ✅ `cloudbuild.yaml` - Updated all services to mount kafka-client-properties secret

## What Changed in cloudbuild.yaml

### Backend Service:
```yaml
# Changed KAFKA_CONFIG path
'--set-env-vars', 'KAFKA_CONFIG=/secrets/client.properties,...'

# Added secret mount
'--set-secrets', '...,/secrets/client.properties=kafka-client-properties:latest'
```

### Consumer Service:
```yaml
# Increased resources
'--memory', '2Gi',
'--cpu', '2',

# Added min instances to keep running
'--min-instances', '1',

# Changed KAFKA_CONFIG path
'--set-env-vars', 'KAFKA_CONFIG=/secrets/client.properties,...'

# Added secret mount
'--set-secrets', '...,/secrets/client.properties=kafka-client-properties:latest'
```

### Producer Service:
```yaml
# Added min instances to keep running
'--min-instances', '1',

# Changed KAFKA_CONFIG path
'--set-env-vars', 'KAFKA_CONFIG=/secrets/client.properties,...'

# Added secret mount (only needs kafka config, not API keys)
'--set-secrets', '/secrets/client.properties=kafka-client-properties:latest'
```

## Before You Deploy

### Step 1: Verify Your Secrets Exist

Run the verification script (on Linux/Mac or WSL):
```bash
chmod +x verify-secrets.sh
./verify-secrets.sh
```

Or manually check:
```bash
# List all secrets
gcloud secrets list --project=563072551472

# Verify kafka-client-properties content
gcloud secrets versions access latest --secret=kafka-client-properties --project=563072551472

# Should show something like:
# bootstrap.servers=pkc-xxxxx.us-east-1.aws.confluent.cloud:9092
# security.protocol=SASL_SSL
# sasl.mechanisms=PLAIN
# sasl.username=YOUR_KEY
# sasl.password=YOUR_SECRET
```

### Step 2: Ensure Service Account Has Permissions

Your Cloud Run services need permission to access secrets:

```bash
# Get the default compute service account
PROJECT_NUMBER="563072551472"
SERVICE_ACCOUNT="${PROJECT_NUMBER}-compute@developer.gserviceaccount.com"

# Grant Secret Manager Secret Accessor role
gcloud projects add-iam-policy-binding $PROJECT_NUMBER \
  --member="serviceAccount:${SERVICE_ACCOUNT}" \
  --role="roles/secretmanager.secretAccessor"
```

## Deploy

```bash
# Submit build
gcloud builds submit --config=cloudbuild.yaml --project=563072551472

# This will:
# 1. Build all 4 Docker images
# 2. Push them to Google Container Registry
# 3. Deploy backend, frontend, consumer, and producer to Cloud Run
# 4. Mount secrets correctly
```

## After Deployment - Verify It's Working

### Check Service Status:
```bash
gcloud run services list --project=563072551472 --region=us-central1
```

All services should show "Ready: True"

### Check Consumer Logs:
```bash
gcloud run services logs read chess-commentary-consumer \
  --project=563072551472 \
  --region=us-central1 \
  --limit=50
```

**Expected output:**
```
[HEALTH] HTTP server started on port 8080
[BOOT] consuming: chess_stream | producing: chess_stream
[KAFKA] Reading config from: /secrets/client.properties
[KAFKA] File exists: True
[KAFKA] Bootstrap servers: pkc-xxxxx.us-east-1.aws.confluent.cloud:9092
[WAIT] Waiting for NEW profile message from UI...
```

### Check Producer Logs:
```bash
gcloud run services logs read chess-commentary-producer \
  --project=563072551472 \
  --region=us-central1 \
  --limit=50
```

**Expected output:**
```
[HEALTH] HTTP server started on port 8080
[WAIT] Waiting for NEW profile message from UI...
[INFO] Please use the UI to analyze a user and send a profile.
```

### Check Backend Logs:
```bash
gcloud run services logs read chess-commentary-backend \
  --project=563072551472 \
  --region=us-central1 \
  --limit=50
```

**Expected output:**
```
[KAFKA] Reading config from: /secrets/client.properties
[KAFKA] File exists: True
[KAFKA] Bootstrap servers: pkc-xxxxx.us-east-1.aws.confluent.cloud:9092
INFO:     Started server process
INFO:     Waiting for application startup.
INFO:     Application startup complete.
```

## Testing the Full Flow

1. **Open your frontend** (get URL from Cloud Run services list)

2. **Analyze a player:**
   - Enter a Lichess username
   - Click "Analyze"
   - Backend should publish profile to Kafka

3. **Producer should pick it up:**
   ```bash
   # Watch producer logs
   gcloud run services logs tail chess-commentary-producer \
     --project=563072551472 \
     --region=us-central1
   ```
   
   Should see:
   ```
   [PROFILE_RECEIVED] username=someuser
   [START] Tracking user=someuser
   [SESSION_START] abc123xyz
   [MOVE] abc123xyz #1 e4
   [MOVE] abc123xyz #2 e5
   ```

4. **Consumer should generate commentary:**
   ```bash
   # Watch consumer logs
   gcloud run services logs tail chess-commentary-consumer \
     --project=563072551472 \
     --region=us-central1
   ```
   
   Should see:
   ```
   [PROFILE] cached game_id=abc123xyz
   [MOVE] game_id=abc123xyz #1 Latest Move=e4 player colour=White
   BUILDING PROMPT
   CALLING LLM - FIRST COMMENTARY
   LLM Response: A bold opening move from White...
   [AUDIO] emitted game_id=abc123xyz move=1
   ```

## Troubleshooting

### Problem: "FileNotFoundError: /secrets/client.properties"
**Cause:** Secret not mounted or wrong path
**Fix:** 
```bash
# Check if secret is mounted in service
gcloud run services describe chess-commentary-consumer \
  --project=563072551472 \
  --region=us-central1 \
  --format="yaml(spec.template.spec.volumes)"
```

### Problem: "Authentication failed" in Kafka logs
**Cause:** Incorrect credentials in kafka-client-properties secret
**Fix:**
```bash
# View current secret content
gcloud secrets versions access latest \
  --secret=kafka-client-properties \
  --project=563072551472

# Update if needed
gcloud secrets versions add kafka-client-properties \
  --data-file=./client.properties \
  --project=563072551472
```

### Problem: Services keep restarting
**Cause:** Health check failing or no HTTP endpoint
**Fix:** Check logs for errors. The health server should start immediately.

### Problem: "No messages being consumed"
**Cause:** Consumer group offset or topic mismatch
**Fix:** 
- Check Confluent Cloud console for topic activity
- Verify consumer group lag
- Check that all services use the same topic name (chess_stream)

### Problem: Consumer receives messages but no commentary generated
**Cause:** API key issues (Gemini or ElevenLabs)
**Fix:**
```bash
# Verify API keys are set
gcloud run services describe chess-commentary-consumer \
  --project=563072551472 \
  --region=us-central1 \
  --format="yaml(spec.template.spec.containers[0].env)"

# Check logs for API errors
gcloud run services logs read chess-commentary-consumer \
  --project=563072551472 \
  --region=us-central1 \
  --limit=100 | grep -i "error\|failed"
```

## Key Differences from Local

| Aspect | Local | Cloud Run |
|--------|-------|-----------|
| client.properties | Copied in Dockerfile | Mounted as secret from Secret Manager |
| API Keys | From .env file | From Secret Manager |
| Health Checks | Not needed | HTTP endpoint required on port 8080 |
| Service Lifecycle | Runs continuously | Needs min-instances=1 to stay alive |
| Logs | Console output | Cloud Logging (view with gcloud) |

## Next Steps

1. ✅ Run `verify-secrets.sh` to check secrets
2. ✅ Deploy with `gcloud builds submit`
3. ✅ Check logs for all 3 services
4. ✅ Test the full flow with a real game
5. ✅ Monitor Confluent Cloud for Kafka activity

## Success Indicators

You'll know it's working when:
- ✅ All 3 services show "Ready: True" in Cloud Run
- ✅ Producer logs show "[MOVE]" messages when games are played
- ✅ Consumer logs show "[AUDIO] emitted" messages
- ✅ Confluent Cloud shows messages in chess_stream topic
- ✅ Frontend receives commentary audio via WebSocket
- ✅ Audio files appear in backend's /audio directory

Good luck with your deployment! 🚀
