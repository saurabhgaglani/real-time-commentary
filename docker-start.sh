#!/bin/bash

# Chess Commentary System - Docker Quick Start Script

set -e

echo "========================================="
echo "Chess Commentary System - Docker Setup"
echo "========================================="
echo ""

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    echo "❌ Error: Docker is not installed"
    echo "Please install Docker from https://docs.docker.com/get-docker/"
    exit 1
fi

# Check if Docker Compose is installed
if ! command -v docker-compose &> /dev/null; then
    echo "❌ Error: Docker Compose is not installed"
    echo "Please install Docker Compose from https://docs.docker.com/compose/install/"
    exit 1
fi

echo "✅ Docker and Docker Compose are installed"
echo ""

# Check for .env file
if [ ! -f ".env" ]; then
    echo "⚠️  Warning: .env file not found"
    echo "Creating .env from template..."
    cp .env.example .env
    echo "✅ Created .env file"
    echo "⚠️  Please edit .env and add your API keys before continuing"
    echo ""
    read -p "Press Enter after you've updated .env with your API keys..."
fi

# Check for client.properties
if [ ! -f "client.properties" ]; then
    echo "⚠️  Warning: client.properties file not found"
    echo "Creating client.properties from template..."
    cp client.properties.example client.properties
    echo "✅ Created client.properties file"
    echo "⚠️  Please edit client.properties and add your Kafka credentials before continuing"
    echo ""
    read -p "Press Enter after you've updated client.properties with your Kafka credentials..."
fi

echo "✅ Configuration files found"
echo ""

# Ask which environment to use
echo "Select environment:"
echo "1) Development (docker-compose.yml)"
echo "2) Production (docker-compose.prod.yml)"
read -p "Enter choice [1-2]: " env_choice

case $env_choice in
    1)
        COMPOSE_FILE="docker-compose.yml"
        echo "Using development configuration"
        ;;
    2)
        COMPOSE_FILE="docker-compose.prod.yml"
        echo "Using production configuration"
        ;;
    *)
        echo "Invalid choice. Using development configuration"
        COMPOSE_FILE="docker-compose.yml"
        ;;
esac

echo ""

# Build images
echo "Building Docker images..."
docker-compose -f $COMPOSE_FILE build

echo ""
echo "✅ Build complete!"
echo ""

# Start services
echo "Starting services..."
docker-compose -f $COMPOSE_FILE up -d

echo ""
echo "✅ Services started!"
echo ""

# Show status
echo "Service Status:"
docker-compose -f $COMPOSE_FILE ps

echo ""
echo "========================================="
echo "🎉 Chess Commentary System is running!"
echo "========================================="
echo ""
echo "Access the application:"
echo "  Frontend:  http://localhost:3000"
echo "  Backend:   http://localhost:8000"
echo "  API Docs:  http://localhost:8000/docs"
echo "  Health:    http://localhost:8000/health"
echo ""
echo "View logs:"
echo "  docker-compose -f $COMPOSE_FILE logs -f"
echo ""
echo "Stop services:"
echo "  docker-compose -f $COMPOSE_FILE down"
echo ""
