# Docker Setup - Files Summary

This document lists all Docker-related files created for the Chess Commentary System.

## Created Files

### 1. Docker Configuration Files

#### `.dockerignore`
- Excludes sensitive files from Docker images
- Prevents `.env`, `client.properties`, `.kiro/` from being included
- Excludes development files, tests, and documentation

#### `Dockerfile.backend`
- Multi-service backend image for Python services
- Installs system dependencies (audio libraries)
- Installs Python packages from `new_requirements.txt`
- Used by: backend API, consumer-commentary, producer-lichess

#### `Dockerfile.frontend`
- Multi-stage build for React frontend
- Stage 1: Build React app with Node.js
- Stage 2: Serve with Nginx
- Optimized for production

#### `nginx.conf`
- Nginx configuration for frontend
- SPA routing support
- Gzip compression
- Security headers
- Static asset caching

### 2. Docker Compose Files

#### `docker-compose.yml` (Development)
- 4 services: backend, consumer-commentary, producer-lichess, frontend
- Development-friendly configuration
- Mounts `client.properties` from host
- Uses `.env` for environment variables
- Shared audio volume

#### `docker-compose.prod.yml` (Production)
- Same services with production optimizations
- Resource limits (CPU, memory)
- Log rotation configured
- Always restart policy
- Optimized for stability

### 3. Configuration Templates

#### `.env.example`
- Template for environment variables
- Lists all required and optional variables
- Safe to commit (no actual secrets)

#### `client.properties.example`
- Template for Kafka configuration
- Shows required Confluent Cloud settings
- Safe to commit (no actual credentials)

### 4. Documentation

#### `DOCKER_SETUP.md`
- Comprehensive Docker setup guide
- Prerequisites and quick start
- Service descriptions
- Docker commands reference
- Troubleshooting guide
- Security notes
- Production recommendations

#### `DOCKER_FILES_SUMMARY.md` (this file)
- Overview of all Docker files
- Purpose and usage of each file

### 5. Quick Start Scripts

#### `docker-start.sh` (Linux/Mac)
- Automated setup script
- Checks for Docker installation
- Creates config files from templates
- Prompts for environment selection
- Builds and starts services
- Shows access URLs

#### `docker-start.bat` (Windows)
- Windows version of quick start script
- Same functionality as shell script
- Uses Windows batch commands

## File Security

### Excluded from Docker Images (.dockerignore)
- ✅ `.env` - API keys
- ✅ `client.properties` - Kafka credentials
- ✅ `.kiro/` - Kiro IDE files
- ✅ `__pycache__/` - Python cache
- ✅ `node_modules/` - Node dependencies
- ✅ Test files and documentation

### Excluded from Git (.gitignore)
- ✅ `.env` - API keys
- ✅ `client.properties` - Kafka credentials
- ✅ `audio/` - Generated audio files
- ✅ Virtual environments
- ✅ Python cache files

### Safe to Commit
- ✅ `.env.example` - Template only
- ✅ `client.properties.example` - Template only
- ✅ All Dockerfiles
- ✅ docker-compose files
- ✅ Documentation

## Usage

### Quick Start (Recommended)

**Linux/Mac:**
```bash
chmod +x docker-start.sh
./docker-start.sh
```

**Windows:**
```cmd
docker-start.bat
```

### Manual Setup

1. **Create configuration files:**
```bash
cp .env.example .env
cp client.properties.example client.properties
# Edit both files with your credentials
```

2. **Build and start (Development):**
```bash
docker-compose build
docker-compose up -d
```

3. **Build and start (Production):**
```bash
docker-compose -f docker-compose.prod.yml build
docker-compose -f docker-compose.prod.yml up -d
```

### View Logs
```bash
# Development
docker-compose logs -f

# Production
docker-compose -f docker-compose.prod.yml logs -f
```

### Stop Services
```bash
# Development
docker-compose down

# Production
docker-compose -f docker-compose.prod.yml down
```

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                     Docker Host                          │
│                                                          │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐ │
│  │   Frontend   │  │   Backend    │  │  Consumer    │ │
│  │   (Nginx)    │  │  (FastAPI)   │  │ Commentary   │ │
│  │   Port 3000  │  │   Port 8000  │  │              │ │
│  └──────────────┘  └──────────────┘  └──────────────┘ │
│                                                          │
│  ┌──────────────┐  ┌──────────────────────────────┐   │
│  │  Producer    │  │     Shared Volume            │   │
│  │  Lichess     │  │     (audio-data)             │   │
│  │              │  │     /app/audio               │   │
│  └──────────────┘  └──────────────────────────────┘   │
│                                                          │
│  ┌──────────────────────────────────────────────────┐  │
│  │  Mounted from Host (not in image):              │  │
│  │  - client.properties (Kafka config)             │  │
│  │  - .env (API keys)                              │  │
│  └──────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────┘
                          │
                          ▼
              ┌───────────────────────┐
              │  Confluent Cloud      │
              │  Kafka Cluster        │
              │  (chess_stream topic) │
              └───────────────────────┘
```

## Services

### Backend (Port 8000)
- REST API endpoints
- WebSocket server for audio streaming
- Health check endpoint
- Serves audio files

### Consumer Commentary
- Consumes move events from Kafka
- Generates commentary using Gemini
- Creates audio using ElevenLabs
- Produces audio events to Kafka

### Producer Lichess
- Waits for profile from UI
- Tracks Lichess games
- Produces move events to Kafka

### Frontend (Port 3000)
- React SPA
- WebSocket client
- Audio playback queue
- User interface

## Environment Variables

### Required
- `ELEVENLABS_API_KEY` - ElevenLabs API key
- `GEMINI_API_KEY` - Google Gemini API key
- Kafka credentials in `client.properties`

### Optional (with defaults)
- `TOPIC_PROFILE_IN=chess_stream`
- `TOPIC_LIVE_MOVES=chess_stream`
- `TOPIC_SESSION_EVENTS=chess_stream`
- `TOPIC_OUT_AUDIO=chess_stream`
- `TOPIC_COMMENTARY_AUDIO=chess_stream`
- `KAFKA_GROUP_ID=commentary-consumer-group-1`
- `AUTO_OFFSET_RESET=latest`
- `POLL_SECONDS=1.0`

## Volumes

### audio-data
- Persists generated audio files
- Shared between backend and consumer-commentary
- Survives container restarts
- Can be backed up or cleared as needed

## Ports

- `3000` - Frontend (HTTP)
- `8000` - Backend API (HTTP/WebSocket)

## Next Steps

1. ✅ Files created
2. ⏭️ Configure `.env` with your API keys
3. ⏭️ Configure `client.properties` with Kafka credentials
4. ⏭️ Run `./docker-start.sh` or `docker-start.bat`
5. ⏭️ Access http://localhost:3000
6. ⏭️ Enjoy live chess commentary!

## Support

For detailed instructions, see `DOCKER_SETUP.md`
