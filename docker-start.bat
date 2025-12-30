@echo off
REM Chess Commentary System - Docker Quick Start Script (Windows)

echo =========================================
echo Chess Commentary System - Docker Setup
echo =========================================
echo.

REM Check if Docker is installed
docker --version >nul 2>&1
if errorlevel 1 (
    echo Error: Docker is not installed
    echo Please install Docker from https://docs.docker.com/get-docker/
    exit /b 1
)

REM Check if Docker Compose is installed
docker-compose --version >nul 2>&1
if errorlevel 1 (
    echo Error: Docker Compose is not installed
    echo Please install Docker Compose from https://docs.docker.com/compose/install/
    exit /b 1
)

echo Docker and Docker Compose are installed
echo.

REM Check for .env file
if not exist ".env" (
    echo Warning: .env file not found
    echo Creating .env from template...
    copy .env.example .env
    echo Created .env file
    echo Please edit .env and add your API keys before continuing
    echo.
    pause
)

REM Check for client.properties
if not exist "client.properties" (
    echo Warning: client.properties file not found
    echo Creating client.properties from template...
    copy client.properties.example client.properties
    echo Created client.properties file
    echo Please edit client.properties and add your Kafka credentials before continuing
    echo.
    pause
)

echo Configuration files found
echo.

REM Ask which environment to use
echo Select environment:
echo 1) Development (docker-compose.yml)
echo 2) Production (docker-compose.prod.yml)
set /p env_choice="Enter choice [1-2]: "

if "%env_choice%"=="1" (
    set COMPOSE_FILE=docker-compose.yml
    echo Using development configuration
) else if "%env_choice%"=="2" (
    set COMPOSE_FILE=docker-compose.prod.yml
    echo Using production configuration
) else (
    echo Invalid choice. Using development configuration
    set COMPOSE_FILE=docker-compose.yml
)

echo.

REM Build images
echo Building Docker images...
docker-compose -f %COMPOSE_FILE% build

echo.
echo Build complete!
echo.

REM Start services
echo Starting services...
docker-compose -f %COMPOSE_FILE% up -d

echo.
echo Services started!
echo.

REM Show status
echo Service Status:
docker-compose -f %COMPOSE_FILE% ps

echo.
echo =========================================
echo Chess Commentary System is running!
echo =========================================
echo.
echo Access the application:
echo   Frontend:  http://localhost:3000
echo   Backend:   http://localhost:8000
echo   API Docs:  http://localhost:8000/docs
echo   Health:    http://localhost:8000/health
echo.
echo View logs:
echo   docker-compose -f %COMPOSE_FILE% logs -f
echo.
echo Stop services:
echo   docker-compose -f %COMPOSE_FILE% down
echo.
pause
