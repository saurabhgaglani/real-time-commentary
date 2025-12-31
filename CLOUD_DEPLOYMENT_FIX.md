# Google Cloud Deployment Fix Guide

## Problems Identified

### 1. ❌ CRITICAL: Kafka client.properties Not Accessible in Cloud Run

**Problem:** Your Dockerfiles copy `client.properties` during build, but in Cloud Run you're storing it as a secret that's never mounted. The secret exists but your containers can't read it.

**Current State:**
- Dockerfile: `COPY client.properties ./config/client.properties` (build-time only)
- Cloud Run: Secret stored but not mounted
- Result: Containers look for `/app/config/client.properties` but file doesn't exist

**Solution Options:**

#### Option A: Mount Secret as Volume (Recommended)
Update your cloudbuild.yaml deployment steps to mount the secret:

```yaml
# For consumer
- name: 'gcr.io/cloud-builders/gcloud'
  args: [
    'run', 'deploy', 'chess-commentary-consumer',
    '--image', 'gcr.io/$PROJECT_ID/chess-commentary-consumer:$BUILD_ID',
    '--region', 'us-central1',
    '--platform', 'managed',
    '--no-traffic',
    '--memory', '1Gi',
    '--cpu', '1',
    '--timeout', '3600',
    '--concurrency', '1',
    '--max-instances', '3',
    '--port', '8080',
    '--set-env-vars', 'KAFKA_CONFIG=/secrets/client.properties,TOPIC_PROFILE_IN=chess_stream,TOPIC_LIVE_MOVES=chess_stream,TOPIC_OUT_AUDIO=chess_stream,KAFKA_GROUP_ID=commentary-consumer-group-1,AUTO_OFFSET_RESET=latest',
    '--set-secrets', 'ELEVENLABS_API_KEY=elevenlabs-api-key:latest,GEMINI_API_KEY=gemini-api-key:latest,YOUR_API_KEY=gemini-api-key:latest,/secrets/client.properties=kafka-client-properties:latest'
  ]
```

Note the change: `--set-secrets` now includes `/secrets/client.properties=kafka-client-properties:latest`

#### Option B: Parse Secret and Use Environment Variables
Modify your code to read Kafka config from environment variables instead of a file.

### 2. ❌ Secret Names Malformed

**Problem:** Your secret paths are concatenated without separators.

**Current (Wrong):**
```
projects/563072551472/secrets/gemini-api-keyprojects/563072551472/secrets/elevenlabs-api-key
```

**Should Be:**
```
projects/563072551472/secrets/gemini-api-key
projects/563072551472/secrets/elevenlabs-api-key
projects/563072551472/secrets/kafka-client-properties
```

**Fix:** The cloudbuild.yaml already uses correct short names (`gemini-api-key:latest`), so this is fine. Just verify your secrets exist with these exact names:

```bash
gcloud secrets list --project=563072551472
```

### 3. ❌ Consumer/Producer Services Need HTTP Health Endpoints

**Problem:** Cloud Run expects HTTP services. Your consumer/producer are long-running Kafka consumers that don't serve HTTP.

**Solution:** Add a simple health check HTTP server to each service.

## Step-by-Step Fix

### Step 1: Verify Secrets Exist

```bash
# List all secrets
gcloud secrets list --project=563072551472

# Check if these exist:
# - gemini-api-key
# - elevenlabs-api-key  
# - kafka-client-properties

# View secret metadata (not content)
gcloud secrets describe kafka-client-properties --project=563072551472
```

### Step 2: Verify kafka-client-properties Content

```bash
# Access the secret content
gcloud secrets versions access latest --secret=kafka-client-properties --project=563072551472

# Should output something like:
# bootstrap.servers=pkc-xxxxx.us-east-1.aws.confluent.cloud:9092
# security.protocol=SASL_SSL
# sasl.mechanisms=PLAIN
# sasl.username=YOUR_KEY
# sasl.password=YOUR_SECRET
```

### Step 3: Update Dockerfiles to Not Copy client.properties

Since we'll mount it as a secret, remove the COPY line:

**Dockerfile.consumer:**
```dockerfile
# Remove or comment out:
# COPY client.properties ./config/client.properties
```

**Dockerfile.producer:**
```dockerfile
# Remove or comment out:
# COPY client.properties ./config/client.properties
```

**Dockerfile.backend:**
```dockerfile
# Remove or comment out:
# COPY client.properties ./config/client.properties
```

### Step 4: Add Health Check Endpoints

Create a new file for health check server:

**backend/health_server.py:**
```python
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler

class HealthHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/health' or self.path == '/':
            self.send_response(200)
            self.send_header('Content-type', 'text/plain')
            self.end_headers()
            self.wfile.write(b'OK')
        else:
            self.send_response(404)
            self.end_headers()
    
    def log_message(self, format, *args):
        # Suppress logs
        pass

def start_health_server(port=8080):
    """Start a simple HTTP health check server in a background thread."""
    server = HTTPServer(('0.0.0.0', port), HealthHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    print(f"[HEALTH] Server started on port {port}", flush=True)
    return server
```

### Step 5: Update Consumer to Include Health Server

**backend/consumer_commentary.py** - Add at the top:
```python
from backend.health_server import start_health_server
```

**In main() function, add after imports:**
```python
def main():
    # Start health check server for Cloud Run
    start_health_server(port=8080)
    
    # ... rest of your existing code
```

### Step 6: Update Producer to Include Health Server

**backend/producer_lichess.py** - Add at the top:
```python
from backend.health_server import start_health_server
```

**In main() function, add after imports:**
```python
def main():
    # Start health check server for Cloud Run
    start_health_server(port=8080)
    
    # ... rest of your existing code
```

### Step 7: Update cloudbuild.yaml

Replace the consumer and producer deployment steps with:

```yaml
  # Deploy consumer service
  - name: 'gcr.io/cloud-builders/gcloud'
    args: [
      'run', 'deploy', 'chess-commentary-consumer',
      '--image', 'gcr.io/$PROJECT_ID/chess-commentary-consumer:$BUILD_ID',
      '--region', 'us-central1',
      '--platform', 'managed',
      '--no-traffic',
      '--memory', '2Gi',
      '--cpu', '2',
      '--timeout', '3600',
      '--concurrency', '1',
      '--max-instances', '3',
      '--min-instances', '1',
      '--port', '8080',
      '--set-env-vars', 'KAFKA_CONFIG=/secrets/client.properties,TOPIC_PROFILE_IN=chess_stream,TOPIC_LIVE_MOVES=chess_stream,TOPIC_OUT_AUDIO=chess_stream,KAFKA_GROUP_ID=commentary-consumer-group-1,AUTO_OFFSET_RESET=latest',
      '--set-secrets', 'ELEVENLABS_API_KEY=elevenlabs-api-key:latest,GEMINI_API_KEY=gemini-api-key:latest,YOUR_API_KEY=gemini-api-key:latest,/secrets/client.properties=kafka-client-properties:latest'
    ]
    id: 'deploy-consumer'
    waitFor: ['push-consumer']

  # Deploy producer service  
  - name: 'gcr.io/cloud-builders/gcloud'
    args: [
      'run', 'deploy', 'chess-commentary-producer',
      '--image', 'gcr.io/$PROJECT_ID/chess-commentary-producer:$BUILD_ID',
      '--region', 'us-central1',
      '--platform', 'managed',
      '--no-traffic',
      '--memory', '1Gi',
      '--cpu', '1',
      '--timeout', '3600',
      '--concurrency', '1',
      '--max-instances', '3',
      '--min-instances', '1',
      '--port', '8080',
      '--set-env-vars', 'KAFKA_CONFIG=/secrets/client.properties,TOPIC_PROFILE_IN=chess_stream,TOPIC_LIVE_MOVES=chess_stream,TOPIC_SESSION_EVENTS=chess_stream,POLL_SECONDS=1.0',
      '--set-secrets', '/secrets/client.properties=kafka-client-properties:latest'
    ]
    id: 'deploy-producer'
    waitFor: ['push-producer']
```

Key changes:
- Added `--min-instances=1` to keep services running
- Added `/secrets/client.properties=kafka-client-properties:latest` to mount the secret
- Updated `KAFKA_CONFIG=/secrets/client.properties` to point to mounted location

### Step 8: Deploy and Test

```bash
# Trigger build
gcloud builds submit --config=cloudbuild.yaml --project=563072551472

# Check logs for consumer
gcloud run services logs read chess-commentary-consumer --project=563072551472 --region=us-central1 --limit=100

# Check logs for producer
gcloud run services logs read chess-commentary-producer --project=563072551472 --region=us-central1 --limit=100

# Check logs for backend
gcloud run services logs read chess-commentary-backend --project=563072551472 --region=us-central1 --limit=100
```

## Debugging Commands

```bash
# Check if services are running
gcloud run services list --project=563072551472 --region=us-central1

# Get service details
gcloud run services describe chess-commentary-consumer --project=563072551472 --region=us-central1

# Check recent logs with timestamps
gcloud run services logs read chess-commentary-consumer \
  --project=563072551472 \
  --region=us-central1 \
  --limit=50 \
  --format="table(timestamp,severity,textPayload)"

# Stream live logs
gcloud run services logs tail chess-commentary-consumer \
  --project=563072551472 \
  --region=us-central1
```

## Expected Log Output After Fix

**Consumer logs should show:**
```
[HEALTH] Server started on port 8080
[BOOT] consuming: chess_stream | producing: chess_stream
[KAFKA] Reading config from: /secrets/client.properties
[KAFKA] File exists: True
[KAFKA] Bootstrap servers: pkc-xxxxx.us-east-1.aws.confluent.cloud:9092
```

**Producer logs should show:**
```
[HEALTH] Server started on port 8080
[WAIT] Waiting for NEW profile message from UI...
```

## Common Issues

### Issue: "FileNotFoundError: /app/config/client.properties"
**Cause:** Secret not mounted correctly
**Fix:** Verify the `--set-secrets` flag includes the file mount

### Issue: "Service keeps restarting"
**Cause:** No HTTP endpoint responding
**Fix:** Ensure health_server.py is imported and started

### Issue: "No messages being consumed"
**Cause:** Consumer group offset or topic mismatch
**Fix:** Check Confluent Cloud console for topic activity and consumer group lag

### Issue: "Authentication failed"
**Cause:** Incorrect Kafka credentials in secret
**Fix:** Verify secret content with `gcloud secrets versions access`
