# Docker Quick Reference

## 🚀 Quick Start

### Option 1: Automated Script (Easiest)
```bash
# Linux/Mac
./docker-start.sh

# Windows
docker-start.bat
```

### Option 2: Using Make (Linux/Mac)
```bash
make start
```

### Option 3: Manual
```bash
# 1. Setup config
cp .env.example .env
cp client.properties.example client.properties
# Edit both files with your credentials

# 2. Build and start
docker-compose up -d
```

## 📋 Common Commands

### Development
```bash
make dev          # Start development environment
make logs         # View logs
make down         # Stop services
make restart      # Restart services
```

### Production
```bash
make prod         # Start production environment
make prod-logs    # View production logs
make prod-down    # Stop production
```

### Maintenance
```bash
make ps           # Show service status
make health       # Check service health
make clean        # Stop and remove volumes
make rebuild      # Rebuild without cache
```

## 🔍 Troubleshooting

### Check Logs
```bash
# All services
make logs

# Specific service
make backend-logs
make consumer-logs
make producer-logs
make frontend-logs
```

### Check Status
```bash
make ps
make health
```

### Restart Service
```bash
docker-compose restart backend
docker-compose restart consumer-commentary
```

### Clean Start
```bash
make clean
make build
make up
```

## 🌐 Access URLs

- **Frontend**: http://localhost:3000
- **Backend API**: http://localhost:8000
- **API Docs**: http://localhost:8000/docs
- **Health Check**: http://localhost:8000/health

## 📁 Important Files

### Must Configure (Not in Git)
- `.env` - API keys
- `client.properties` - Kafka credentials

### Templates (Safe to commit)
- `.env.example`
- `client.properties.example`

### Docker Files
- `Dockerfile.backend` - Backend services
- `Dockerfile.frontend` - Frontend build
- `docker-compose.yml` - Development
- `docker-compose.prod.yml` - Production
- `.dockerignore` - Exclude files

## 🔒 Security Checklist

- ✅ `.env` excluded from Git
- ✅ `client.properties` excluded from Git
- ✅ `.kiro/` excluded from Docker images
- ✅ Secrets mounted at runtime (not baked in)
- ✅ `.dockerignore` configured

## 📊 Service Architecture

```
Frontend (3000) → Backend (8000) → Kafka
                      ↓
                  WebSocket
                      ↓
                   Browser
```

## 🛠️ Development Workflow

1. Make code changes
2. Rebuild: `make rebuild`
3. Restart: `make restart`
4. Check logs: `make logs`

## 📦 Volumes

### Audio Data
```bash
# List volumes
docker volume ls

# Inspect
docker volume inspect real-time-commentary_audio-data

# Backup
docker run --rm -v real-time-commentary_audio-data:/data -v $(pwd):/backup alpine tar czf /backup/audio-backup.tar.gz /data

# Restore
docker run --rm -v real-time-commentary_audio-data:/data -v $(pwd):/backup alpine tar xzf /backup/audio-backup.tar.gz -C /
```

## 🐛 Common Issues

### "Cannot connect to Kafka"
- Check `client.properties` credentials
- Verify Kafka cluster is accessible
- Check logs: `make consumer-logs`

### "API keys invalid"
- Verify `.env` has correct keys
- Restart services: `make restart`

### "Port already in use"
- Stop conflicting services
- Or change ports in docker-compose.yml

### "No audio playing"
- Check browser console (F12)
- Verify WebSocket connection
- Check backend logs: `make backend-logs`

## 📚 Full Documentation

- `DOCKER_SETUP.md` - Complete setup guide
- `DOCKER_FILES_SUMMARY.md` - File descriptions
- `README.md` - Project overview

## 💡 Tips

- Use `make help` to see all commands
- Use `make logs` to debug issues
- Use `make clean` for fresh start
- Check `make health` regularly
- Production: use `docker-compose.prod.yml`

## 🎯 Next Steps

1. Configure `.env` and `client.properties`
2. Run `make start`
3. Open http://localhost:3000
4. Analyze a Lichess user
5. Start a live game
6. Enjoy commentary! 🎵
