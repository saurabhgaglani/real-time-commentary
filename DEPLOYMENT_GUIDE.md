# Deployment Guide - Fresh Installation

This guide shows you how to deploy the Chess Commentary System in a new folder/server.

## Prerequisites

- Docker Engine 20.10+
- Docker Compose 2.0+
- Git (optional, for cloning)
- Your API keys ready:
  - ElevenLabs API key
  - Google Gemini API key
  - Confluent Cloud Kafka credentials

## Option 1: Clone from Git Repository

### Step 1: Clone the Repository
```bash
# Clone the repository
git clone <your-repo-url> chess-commentary
cd chess-commentary
```

### Step 2: Configure Secrets
```bash
# Create .env file
cp .env.example .env

# Edit .env and add your API keys
nano .env  # or use any text editor
```

Add your keys:
```bash
ELEVENLABS_API_KEY=sk_your_actual_key_here
GEMINI_API_KEY=AIza_your_actual_key_here
```

```bash
# Create client.properties file
cp client.properties.example client.properties

# Edit client.properties and add Kafka credentials
nano client.properties
```

Add your Kafka config:
```properties
bootstrap.servers=your-cluster.region.provider.confluent.cloud:9092
security.protocol=SASL_SSL
sasl.mechanisms=PLAIN
sasl.username=your-api-key
sasl.password=your-api-secret
session.timeout.ms=45000
```

### Step 3: Run the Application
```bash
# Option A: Use the automated script
chmod +x docker-start.sh
./docker-start.sh

# Option B: Use Make
make start

# Option C: Manual
docker-compose build
docker-compose up -d
```

### Step 4: Access the Application
- Frontend: http://localhost:3000
- Backend: http://localhost:8000

---

## Option 2: Manual Setup (No Git)

### Step 1: Create Project Directory
```bash
mkdir chess-commentary
cd chess-commentary
```

### Step 2: Copy Required Files

You need to copy these files from your development machine:

**Essential Files:**
```
chess-commentary/
├── backend/
│   ├── main.py
│   ├── websocket_manager.py
│   ├── consumer_commentary.py
│   └── producer_lichess.py
├── frontend/
│   ├── src/
│   ├── package.json
│   ├── vite.config.js
│   └── ... (all frontend files)
├── new_requirements.txt
├── Dockerfile.backend
├── Dockerfile.frontend
├── docker-compose.yml
├── nginx.conf
├── .dockerignore
├── .env.example
└── client.properties.example
```

**Optional but Recommended:**
```
├── docker-compose.prod.yml
├── docker-start.sh
├── docker-start.bat
├── Makefile
├── DOCKER_SETUP.md
└── DOCKER_QUICK_REFERENCE.md
```

### Step 3: Configure Secrets

```bash
# Create .env from template
cp .env.example .env

# Edit .env
nano .env
```

Add your keys:
```bash
ELEVENLABS_API_KEY=sk_your_actual_key_here
GEMINI_API_KEY=AIza_your_actual_key_here
TOPIC_PROFILE_IN=chess_stream
TOPIC_LIVE_MOVES=chess_stream
TOPIC_SESSION_EVENTS=chess_stream
TOPIC_OUT_AUDIO=chess_stream
TOPIC_COMMENTARY_AUDIO=chess_stream
```

```bash
# Create client.properties from template
cp client.properties.example client.properties

# Edit client.properties
nano client.properties
```

Add Kafka config:
```properties
bootstrap.servers=your-cluster.region.provider.confluent.cloud:9092
security.protocol=SASL_SSL
sasl.mechanisms=PLAIN
sasl.username=your-api-key
sasl.password=your-api-secret
session.timeout.ms=45000
```

### Step 4: Build and Run

```bash
# Build images
docker-compose build

# Start services
docker-compose up -d

# Check status
docker-compose ps

# View logs
docker-compose logs -f
```

---

## Option 3: Using Docker Hub (If you push images)

### Step 1: Pull Images
```bash
# Pull pre-built images (if available)
docker pull your-dockerhub-username/chess-commentary-backend:latest
docker pull your-dockerhub-username/chess-commentary-frontend:latest
```

### Step 2: Create Minimal Setup

Create `docker-compose.yml`:
```yaml
version: '3.8'

services:
  backend:
    image: your-dockerhub-username/chess-commentary-backend:latest
    ports:
      - "8000:8000"
    environment:
      - KAFKA_CONFIG=/app/config/client.properties
      - ELEVENLABS_API_KEY=${ELEVENLABS_API_KEY}
      - GEMINI_API_KEY=${GEMINI_API_KEY}
    volumes:
      - ./client.properties:/app/config/client.properties:ro
      - audio-data:/app/audio

  consumer-commentary:
    image: your-dockerhub-username/chess-commentary-backend:latest
    command: ["python", "-u", "backend/consumer_commentary.py"]
    environment:
      - KAFKA_CONFIG=/app/config/client.properties
      - ELEVENLABS_API_KEY=${ELEVENLABS_API_KEY}
      - GEMINI_API_KEY=${GEMINI_API_KEY}
    volumes:
      - ./client.properties:/app/config/client.properties:ro
      - audio-data:/app/audio

  producer-lichess:
    image: your-dockerhub-username/chess-commentary-backend:latest
    command: ["python", "-u", "backend/producer_lichess.py"]
    environment:
      - KAFKA_CONFIG=/app/config/client.properties
    volumes:
      - ./client.properties:/app/config/client.properties:ro

  frontend:
    image: your-dockerhub-username/chess-commentary-frontend:latest
    ports:
      - "3000:80"

volumes:
  audio-data:
```

### Step 3: Configure and Run
```bash
# Create .env and client.properties as shown above
# Then start
docker-compose up -d
```

---

## Verification Steps

### 1. Check Services are Running
```bash
docker-compose ps
```

Expected output:
```
NAME                          STATUS    PORTS
chess-commentary-backend      Up        0.0.0.0:8000->8000/tcp
chess-commentary-consumer     Up
chess-commentary-producer     Up
chess-commentary-frontend     Up        0.0.0.0:3000->80/tcp
```

### 2. Check Health
```bash
# Backend health
curl http://localhost:8000/health

# Expected: {"status":"ok"}
```

### 3. Check Logs
```bash
# All services
docker-compose logs

# Specific service
docker-compose logs backend
docker-compose logs consumer-commentary
docker-compose logs producer-lichess
```

### 4. Access Frontend
Open browser: http://localhost:3000

You should see the Chess Commentary interface.

---

## Production Deployment

### For Production Server

1. **Use production compose file:**
```bash
docker-compose -f docker-compose.prod.yml up -d
```

2. **Set up reverse proxy (Nginx/Traefik):**
```nginx
# Example Nginx config
server {
    listen 80;
    server_name your-domain.com;

    location / {
        proxy_pass http://localhost:3000;
    }

    location /api {
        proxy_pass http://localhost:8000;
    }

    location /ws {
        proxy_pass http://localhost:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }
}
```

3. **Enable HTTPS with Let's Encrypt:**
```bash
certbot --nginx -d your-domain.com
```

4. **Set up monitoring:**
```bash
# Add to docker-compose.prod.yml
  prometheus:
    image: prom/prometheus
    volumes:
      - ./prometheus.yml:/etc/prometheus/prometheus.yml

  grafana:
    image: grafana/grafana
    ports:
      - "3001:3000"
```

---

## Troubleshooting

### Services won't start
```bash
# Check Docker is running
docker ps

# Check logs for errors
docker-compose logs

# Rebuild images
docker-compose build --no-cache
```

### Can't connect to Kafka
```bash
# Verify client.properties
cat client.properties

# Test from container
docker-compose exec backend python backend/test_kafka_consumer.py
```

### Frontend not loading
```bash
# Check frontend logs
docker-compose logs frontend

# Check if port 3000 is available
netstat -an | grep 3000

# Try accessing directly
curl http://localhost:3000
```

### Audio not playing
```bash
# Check consumer logs
docker-compose logs consumer-commentary

# Check audio files
docker-compose exec backend ls -la /app/audio

# Check WebSocket in browser console (F12)
```

---

## File Checklist

Before deploying, ensure you have:

- ✅ `Dockerfile.backend`
- ✅ `Dockerfile.frontend`
- ✅ `docker-compose.yml`
- ✅ `nginx.conf`
- ✅ `.dockerignore`
- ✅ `new_requirements.txt`
- ✅ `backend/` folder with all Python files
- ✅ `frontend/` folder with all React files
- ✅ `.env` (configured with your keys)
- ✅ `client.properties` (configured with Kafka)

---

## Quick Commands Reference

```bash
# Start
docker-compose up -d

# Stop
docker-compose down

# Restart
docker-compose restart

# Logs
docker-compose logs -f

# Status
docker-compose ps

# Rebuild
docker-compose build

# Clean start
docker-compose down -v
docker-compose build
docker-compose up -d
```

---

## Next Steps

1. ✅ Deploy to new folder
2. ✅ Configure secrets
3. ✅ Start services
4. ⏭️ Test with a Lichess game
5. ⏭️ Set up monitoring
6. ⏭️ Configure backups
7. ⏭️ Enable HTTPS (production)

---

## Support

- Full setup guide: `DOCKER_SETUP.md`
- Quick reference: `DOCKER_QUICK_REFERENCE.md`
- File descriptions: `DOCKER_FILES_SUMMARY.md`
