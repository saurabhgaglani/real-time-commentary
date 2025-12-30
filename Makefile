# Chess Commentary System - Makefile
# Convenient commands for Docker operations

.PHONY: help build up down logs restart clean setup dev prod

# Default target
help:
	@echo "Chess Commentary System - Docker Commands"
	@echo ""
	@echo "Setup:"
	@echo "  make setup      - Create config files from templates"
	@echo "  make build      - Build all Docker images"
	@echo ""
	@echo "Development:"
	@echo "  make dev        - Start development environment"
	@echo "  make up         - Start all services (alias for dev)"
	@echo "  make down       - Stop all services"
	@echo "  make restart    - Restart all services"
	@echo "  make logs       - View logs (follow mode)"
	@echo ""
	@echo "Production:"
	@echo "  make prod       - Start production environment"
	@echo "  make prod-down  - Stop production environment"
	@echo "  make prod-logs  - View production logs"
	@echo ""
	@echo "Maintenance:"
	@echo "  make clean      - Stop services and remove volumes"
	@echo "  make rebuild    - Rebuild images without cache"
	@echo "  make ps         - Show service status"
	@echo ""

# Setup configuration files
setup:
	@echo "Creating configuration files..."
	@if [ ! -f .env ]; then \
		cp .env.example .env; \
		echo "✅ Created .env - Please edit with your API keys"; \
	else \
		echo "⚠️  .env already exists"; \
	fi
	@if [ ! -f client.properties ]; then \
		cp client.properties.example client.properties; \
		echo "✅ Created client.properties - Please edit with Kafka credentials"; \
	else \
		echo "⚠️  client.properties already exists"; \
	fi

# Build images
build:
	@echo "Building Docker images..."
	docker-compose build

rebuild:
	@echo "Rebuilding Docker images (no cache)..."
	docker-compose build --no-cache

# Development environment
dev: up

up:
	@echo "Starting development environment..."
	docker-compose up -d
	@echo ""
	@echo "✅ Services started!"
	@echo "Frontend:  http://localhost:3000"
	@echo "Backend:   http://localhost:8000"
	@echo "API Docs:  http://localhost:8000/docs"

down:
	@echo "Stopping services..."
	docker-compose down

restart:
	@echo "Restarting services..."
	docker-compose restart

logs:
	docker-compose logs -f

ps:
	docker-compose ps

# Production environment
prod:
	@echo "Starting production environment..."
	docker-compose -f docker-compose.prod.yml up -d
	@echo ""
	@echo "✅ Production services started!"
	@echo "Frontend:  http://localhost:80"
	@echo "Backend:   http://localhost:8000"

prod-down:
	@echo "Stopping production services..."
	docker-compose -f docker-compose.prod.yml down

prod-logs:
	docker-compose -f docker-compose.prod.yml logs -f

prod-ps:
	docker-compose -f docker-compose.prod.yml ps

# Cleanup
clean:
	@echo "Stopping services and removing volumes..."
	docker-compose down -v
	@echo "✅ Cleanup complete"

clean-all:
	@echo "Removing everything (containers, volumes, images)..."
	docker-compose down -v --rmi all
	@echo "✅ Complete cleanup done"

# Individual service commands
backend-logs:
	docker-compose logs -f backend

consumer-logs:
	docker-compose logs -f consumer-commentary

producer-logs:
	docker-compose logs -f producer-lichess

frontend-logs:
	docker-compose logs -f frontend

# Health checks
health:
	@echo "Checking service health..."
	@curl -f http://localhost:8000/health || echo "❌ Backend not responding"
	@curl -f http://localhost:3000 > /dev/null 2>&1 && echo "✅ Frontend is up" || echo "❌ Frontend not responding"

# Quick start (setup + build + up)
start: setup build up
	@echo ""
	@echo "🎉 Chess Commentary System is running!"
	@echo "Visit http://localhost:3000 to get started"
