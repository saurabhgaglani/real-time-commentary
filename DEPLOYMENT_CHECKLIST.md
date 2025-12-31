# Google Cloud Deployment Checklist

Use this checklist to ensure your deployment succeeds.

## Pre-Deployment Checks

### ☐ 1. Verify Secrets Exist

Run the verification script:
```bash
# On Linux/Mac/WSL:
chmod +x verify-secrets.sh
./verify-secrets.sh

# On Windows:
verify-secrets.bat
```

Or manually:
```bash
gcloud secrets list --project=563072551472
```

You should see:
- ✅ `gemini-api-key`
- ✅ `elevenlabs-api-key`
- ✅ `kafka-client-properties`

### ☐ 2. Verify kafka-client-properties Content

```bash
gcloud secrets versions access latest --secret=kafka-client-properties --project=563072551472
```

Must contain:
- ✅ `bootstrap.servers=...`
- ✅ `security.protocol=SASL_SSL`
- ✅ `sasl.mechanisms=PLAIN`
- ✅ `sasl.username=...`
- ✅ `sasl.password=...`

### ☐ 3. Verify Service Account Permissions

```bash
# Grant Secret Manager access to default compute service account
gcloud projects add-iam-policy-binding 563072551472 \
  --member="serviceAccount:563072551472-compute@developer.gserviceaccount.com" \
  --role="roles/secretmanager.secretAccessor"
```

### ☐ 4. Review Changes

Files that were modified:
- ✅ `backend/health_server.py` (NEW)
- ✅ `backend/consumer_commentary.py` (health server added)
- ✅ `backend/producer_lichess.py` (health server added)
- ✅ `Dockerfile.backend` (secret mount prep)
- ✅ `Dockerfile.consumer` (secret mount prep)
- ✅ `Dockerfile.producer` (secret mount prep)
- ✅ `cloudbuild.yaml` (secret mounting configured)

## Deployment

### ☐ 5. Submit Build

```bash
gcloud builds submit --config=cloudbuild.yaml --project=563072551472
```

This will take 5-10 minutes. Watch for:
- ✅ All 4 images build successfully
- ✅ All 4 images push to GCR
- ✅ All 4 services deploy to Cloud Run

### ☐ 6. Check Build Status

```bash
# List recent builds
gcloud builds list --project=563072551472 --limit=5

# View specific build logs
gcloud builds log <BUILD_ID> --project=563072551472
```

## Post-Deployment Verification

### ☐ 7. Check Service Status

```bash
gcloud run services list --project=563072551472 --region=us-central1
```

All services should show:
- ✅ STATUS: Ready
- ✅ URL: (for backend and frontend)

### ☐ 8. Check Backend Logs

```bash
gcloud run services logs read chess-commentary-backend \
  --project=563072551472 \
  --region=us-central1 \
  --limit=50
```

Look for:
- ✅ `[KAFKA] File exists: True`
- ✅ `[KAFKA] Bootstrap servers: pkc-...`
- ✅ `Application startup complete`

### ☐ 9. Check Consumer Logs

```bash
gcloud run services logs read chess-commentary-consumer \
  --project=563072551472 \
  --region=us-central1 \
  --limit=50
```

Look for:
- ✅ `[HEALTH] HTTP server started on port 8080`
- ✅ `[BOOT] consuming: chess_stream | producing: chess_stream`
- ✅ `[KAFKA] File exists: True`
- ✅ `[KAFKA] Bootstrap servers: pkc-...`

### ☐ 10. Check Producer Logs

```bash
gcloud run services logs read chess-commentary-producer \
  --project=563072551472 \
  --region=us-central1 \
  --limit=50
```

Look for:
- ✅ `[HEALTH] HTTP server started on port 8080`
- ✅ `[WAIT] Waiting for NEW profile message from UI...`

## Functional Testing

### ☐ 11. Get Frontend URL

```bash
gcloud run services describe chess-commentary-frontend \
  --project=563072551472 \
  --region=us-central1 \
  --format="value(status.url)"
```

### ☐ 12. Test Profile Analysis

1. Open frontend URL in browser
2. Enter a Lichess username (e.g., "DrNykterstein")
3. Click "Analyze"
4. Check backend logs for profile publish:
   ```bash
   gcloud run services logs read chess-commentary-backend \
     --project=563072551472 \
     --region=us-central1 \
     --limit=20 | grep "KAFKA"
   ```
   Should see: `[KAFKA] Profile published for <username>`

### ☐ 13. Test Live Game Tracking

1. Make sure the player is in an active game on Lichess
2. Check producer logs:
   ```bash
   gcloud run services logs tail chess-commentary-producer \
     --project=563072551472 \
     --region=us-central1
   ```
   Should see:
   - ✅ `[SESSION_START] <game_id>`
   - ✅ `[MOVE] <game_id> #1 e4`
   - ✅ `[MOVE] <game_id> #2 e5`

### ☐ 14. Test Commentary Generation

Check consumer logs while game is active:
```bash
gcloud run services logs tail chess-commentary-consumer \
  --project=563072551472 \
  --region=us-central1
```

Should see:
- ✅ `[PROFILE] cached game_id=<game_id>`
- ✅ `[MOVE] game_id=<game_id> #1 Latest Move=e4`
- ✅ `CALLING LLM`
- ✅ `LLM Response: ...`
- ✅ `[AUDIO] emitted game_id=<game_id> move=1`

### ☐ 15. Verify Kafka Activity

Check Confluent Cloud console:
1. Go to your cluster
2. Navigate to Topics → chess_stream
3. Check Messages tab
4. Should see:
   - ✅ Profile messages
   - ✅ Move messages
   - ✅ Commentary audio messages

### ☐ 16. Test WebSocket Connection

1. Open browser console on frontend
2. Should see WebSocket connection established
3. When commentary is generated, should receive messages

## Troubleshooting

### If Backend Can't Read client.properties:

```bash
# Check if secret is mounted
gcloud run services describe chess-commentary-backend \
  --project=563072551472 \
  --region=us-central1 \
  --format="yaml(spec.template.spec.volumes)"

# Should show volume with secret mount
```

### If Consumer Not Generating Commentary:

```bash
# Check for errors
gcloud run services logs read chess-commentary-consumer \
  --project=563072551472 \
  --region=us-central1 \
  --limit=100 | grep -i "error\|exception\|failed"

# Check API key access
gcloud run services describe chess-commentary-consumer \
  --project=563072551472 \
  --region=us-central1 \
  --format="yaml(spec.template.spec.containers[0].env)"
```

### If Services Keep Restarting:

```bash
# Check health endpoint
CONSUMER_URL=$(gcloud run services describe chess-commentary-consumer \
  --project=563072551472 \
  --region=us-central1 \
  --format="value(status.url)")

curl -H "Authorization: Bearer $(gcloud auth print-identity-token)" \
  $CONSUMER_URL/health
```

### If No Kafka Messages:

1. Check Confluent Cloud cluster status
2. Verify topic exists: `chess_stream`
3. Check consumer group lag in Confluent Cloud
4. Verify credentials in kafka-client-properties secret

## Success Criteria

✅ All services show "Ready" status
✅ Backend can read kafka-client-properties
✅ Consumer and Producer have health endpoints responding
✅ Profile analysis publishes to Kafka
✅ Producer tracks live games and publishes moves
✅ Consumer generates commentary for moves
✅ Commentary audio messages appear in Kafka
✅ Frontend receives commentary via WebSocket

## Rollback (If Needed)

If deployment fails and you need to rollback:

```bash
# List previous revisions
gcloud run revisions list --service=chess-commentary-consumer \
  --project=563072551472 \
  --region=us-central1

# Rollback to previous revision
gcloud run services update-traffic chess-commentary-consumer \
  --to-revisions=<PREVIOUS_REVISION>=100 \
  --project=563072551472 \
  --region=us-central1
```

## Monitoring

Set up continuous monitoring:

```bash
# Stream consumer logs
gcloud run services logs tail chess-commentary-consumer \
  --project=563072551472 \
  --region=us-central1

# Stream producer logs
gcloud run services logs tail chess-commentary-producer \
  --project=563072551472 \
  --region=us-central1
```

## Notes

- Consumer needs 2Gi memory and 2 CPU for AI processing
- Producer and Consumer have `--min-instances=1` to stay running
- All services now have health check endpoints on port 8080
- Secrets are mounted at `/secrets/` instead of copied during build
- KAFKA_CONFIG env var points to `/secrets/client.properties`

---

**Last Updated:** After fixing secret mounting and health check issues
**Status:** Ready for deployment ✅
