# Docker Setup Guide - Chess Commentary System

This guide explains how to build and run the Chess Commentary System using Docker.

## Prerequisites

- Docker Engine 20.10+
- Docker Compose 2.0+
- Confluent Cloud Kafka cluster (or compatible Kafka service)
- ElevenLabs API key
- Google Gemini API key

## Quick Start

### 1. Configure Environment Variables

Copy the example files and fill in your credentials:

```bash
# Copy environment template
cp .env.example .env

# Copy Kafka config template
cp client.properties.example client.properties
```

Edit `.env` and add your API keys:
```bash
ELEVENLABS_API_KEY=sk_your_actual_key_here
GEMINI_API_KEY=AIza_your_actual_key_here
```

Edit `client.properties` and add your Kafka credentials:
```properties
bootstrap.servers=your-cluster.region.provider.confluent.cloud:9092
sasl.username=your-api-key
sasl.password=your-api-secret
```

### 2. Build and Start Services

```bash
# Build all images
docker-compose build

# Start all services
docker-compose up -d

# View logs
docker-compose logs -f
```

### 3. Access the Application

- **Frontend**: http://localhost:3000
- **Backend API**: http://localhost:8000
- **API Docs**: http://localhost:8000/docs
- **Health Check**: http://localhost:8000/health

## Services

The system consists of 4 services:

### 1. Backend (FastAPI)
- **Port**: 8000
- **Purpose**: REST API and WebSocket server
- **Health**: http://localhost:8000/health

### 2. Consumer Commentary
- **Purpose**: Generates audio commentary from game moves
- **Consumes**: `chess_stream` topic (move events)
- **Produces**: `chess_stream` topic (audio events)

### 3. Producer Lichess
- **Purpose**: Tracks Lichess games and produces move events
- **Consumes**: `chess_stream` topic (profile events)
- **Produces**: `chess_stream` topic (move events)

### 4. Frontend (React + Nginx)
- **Port**: 3000
- **Purpose**: User interface for commentary playback

## Docker Commands

### Start Services
```bash
# Start all services
docker-compose up -d

# Start specific service
docker-compose up -d backend

# Start with logs
docker-compose up
```

### Stop Services
```bash
# Stop all services
docker-compose down

# Stop and remove volumes
docker-compose down -v
```

### View Logs
```bash
# All services
docker-compose logs -f

# Specific service
docker-compose logs -f backend
docker-compose logs -f consumer-commentary
docker-compose logs -f producer-lichess
docker-compose logs -f frontend
```

### Rebuild Services
```bash
# Rebuild all
docker-compose build

# Rebuild specific service
docker-compose build backend

# Rebuild without cache
docker-compose build --no-cache
```

### Restart Services
```bash
# Restart all
docker-compose restart

# Restart specific service
docker-compose restart backend
```

## Volumes

### Audio Data
Audio files are persisted in a Docker volume:
```bash
# List volumes
docker volume ls

# Inspect audio volume
docker volume inspect real-time-commentary_audio-data

# Remove volume (deletes all audio)
docker volume rm real-time-commentary_audio-data
```

## Environment Variables

### Required
- `ELEVENLABS_API_KEY` - ElevenLabs TTS API key
- `GEMINI_API_KEY` - Google Gemini API key
- Kafka credentials in `client.properties`

### Optional
- `TOPIC_PROFILE_IN` - Kafka topic for profiles (default: chess_stream)
- `TOPIC_LIVE_MOVES` - Kafka topic for moves (default: chess_stream)
- `TOPIC_SESSION_EVENTS` - Kafka topic for sessions (default: chess_stream)
- `TOPIC_OUT_AUDIO` - Kafka topic for audio output (default: chess_stream)
- `TOPIC_COMMENTARY_AUDIO` - Kafka topic for audio consumption (default: chess_stream)
- `KAFKA_GROUP_ID` - Consumer group ID (default: commentary-consumer-group-1)
- `AUTO_OFFSET_RESET` - Kafka offset reset (default: latest)
- `POLL_SECONDS` - Lichess polling interval (default: 1.0)

## Troubleshooting

### Services Won't Start

**Check logs:**
```bash
docker-compose logs backend
```

**Common issues:**
- Missing `.env` file → Copy from `.env.example`
- Missing `client.properties` → Copy from `client.properties.example`
- Invalid API keys → Check your credentials
- Kafka connection failed → Verify `client.properties`

### Backend Health Check Failing

```bash
# Check backend logs
docker-compose logs backend

# Test health endpoint
curl http://localhost:8000/health
```

### Audio Not Playing

1. Check consumer-commentary logs:
```bash
docker-compose logs consumer-commentary
```

2. Verify audio files are being created:
```bash
docker-compose exec backend ls -la /app/audio
```

3. Check WebSocket connection in browser console (F12)

### Kafka Connection Issues

1. Verify `client.properties` is mounted:
```bash
docker-compose exec backend cat /app/config/client.properties
```

2. Test Kafka connectivity:
```bash
docker-compose exec backend python backend/test_kafka_consumer.py
```

## Security Notes

### Secrets Management

**Never commit these files:**
- `.env` - Contains API keys
- `client.properties` - Contains Kafka credentials

**These files are excluded via:**
- `.dockerignore` - Prevents inclusion in Docker images
- `.gitignore` - Prevents Git commits

### Production Deployment

For production, use proper secrets management:

**Docker Swarm:**
```bash
docker secret create kafka_config client.properties
docker secret create api_keys .env
```

**Kubernetes:**
```bash
kubectl create secret generic kafka-config --from-file=client.properties
kubectl create secret generic api-keys --from-env-file=.env
```

## Development vs Production

### Development (Current Setup)
- Uses `docker-compose.yml`
- Mounts `client.properties` from host
- Environment variables from `.env` file
- Hot reload disabled (rebuild required)

### Production Recommendations
1. Use Docker secrets or Kubernetes secrets
2. Enable HTTPS/TLS
3. Add authentication to API endpoints
4. Use managed Kafka service
5. Implement proper logging and monitoring
6. Set resource limits in docker-compose

## Monitoring

### Check Service Status
```bash
docker-compose ps
```

### Resource Usage
```bash
docker stats
```

### Health Checks
```bash
# Backend
curl http://localhost:8000/health

# All services
docker-compose ps
```

## Cleanup

### Remove Everything
```bash
# Stop and remove containers, networks
docker-compose down

# Also remove volumes (deletes audio files)
docker-compose down -v

# Remove images
docker-compose down --rmi all
```

### Clean Docker System
```bash
# Remove unused containers, networks, images
docker system prune

# Remove everything including volumes
docker system prune -a --volumes
```

## Next Steps

1. Configure your API keys in `.env`
2. Set up Kafka credentials in `client.properties`
3. Start services: `docker-compose up -d`
4. Open frontend: http://localhost:3000
5. Analyze a Lichess user
6. Start a live game and enjoy commentary!

## Support

For issues or questions:
1. Check logs: `docker-compose logs -f`
2. Review troubleshooting section above
3. Verify all credentials are correct
4. Ensure Kafka cluster is accessible
