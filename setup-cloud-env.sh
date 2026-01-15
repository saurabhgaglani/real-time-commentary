#!/bin/bash

# Chess Commentary System - Cloud Environment Setup
# Run this script before deployment to set up your Google Cloud environment

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}🔧 Chess Commentary System - Cloud Environment Setup${NC}"
echo "======================================================="

# Check if gcloud is installed
if ! command -v gcloud &> /dev/null; then
    echo -e "${RED}❌ Google Cloud CLI not found.${NC}"
    echo -e "${YELLOW}Please install it from: https://cloud.google.com/sdk/docs/install${NC}"
    exit 1
fi

echo -e "${GREEN}✅ Google Cloud CLI found${NC}"

# Check if user is logged in
if ! gcloud auth list --filter=status:ACTIVE --format="value(account)" | grep -q .; then
    echo -e "${YELLOW}🔐 Please login to Google Cloud...${NC}"
    gcloud auth login
fi

echo -e "${GREEN}✅ Authenticated with Google Cloud${NC}"

# Get or set project ID
PROJECT_ID=$(gcloud config get-value project 2>/dev/null)
if [ -z "$PROJECT_ID" ]; then
    echo -e "${YELLOW}📝 No project set. Let's create or select one...${NC}"
    echo ""
    echo "Options:"
    echo "1. Create a new project"
    echo "2. Use an existing project"
    read -p "Choose option (1 or 2): " choice

    if [ "$choice" = "1" ]; then
        read -p "Enter new project ID (lowercase, numbers, hyphens only): " new_project_id
        echo -e "${YELLOW}🏗️  Creating project: $new_project_id${NC}"
        gcloud projects create "$new_project_id" --name="Chess Commentary System"
        gcloud config set project "$new_project_id"
        PROJECT_ID="$new_project_id"

        echo -e "${YELLOW}💳 Please enable billing for this project:${NC}"
        echo "https://console.cloud.google.com/billing/linkedaccount?project=$PROJECT_ID"
        read -p "Press Enter after enabling billing..."

    else
        echo -e "${YELLOW}📋 Available projects:${NC}"
        gcloud projects list --format="table(projectId,name)"
        read -p "Enter project ID to use: " existing_project_id
        gcloud config set project "$existing_project_id"
        PROJECT_ID="$existing_project_id"
    fi
fi

echo -e "${GREEN}✅ Using project: $PROJECT_ID${NC}"

# Check required files
echo -e "${YELLOW}🔍 Checking required files...${NC}"

if [ ! -f ".env" ]; then
    echo -e "${RED}❌ .env file not found${NC}"
    echo -e "${YELLOW}Creating .env template...${NC}"
    cat > .env << EOF
ELEVENLABS_API_KEY=your_elevenlabs_api_key_here
GEMINI_API_KEY=your_gemini_api_key_here
# Kafka parameters
TOPIC_PROFILE_IN="chess_stream"
TOPIC_LIVE_MOVES="chess_stream"
TOPIC_SESSION_EVENTS="chess_stream"
TOPIC_COMMENTARY_AUDIO="chess_stream"
TOPIC_OUT_AUDIO="chess_stream"
EOF
    echo -e "${YELLOW}⚠️  Please edit .env file with your actual API keys before deployment${NC}"
    echo -e "${YELLOW}   - Get ElevenLabs API key from: https://elevenlabs.io/app/settings/api-keys${NC}"
    echo -e "${YELLOW}   - Get Gemini API key from: https://aistudio.google.com/app/apikey${NC}"
else
    echo -e "${GREEN}✅ .env file found${NC}"
fi

if [ ! -f "client.properties" ]; then
    echo -e "${RED}❌ client.properties file not found${NC}"
    echo -e "${YELLOW}Creating client.properties template...${NC}"
    cat > client.properties << EOF
# Kafka Configuration
# Replace with your actual Confluent Cloud credentials
bootstrap.servers=your-kafka-bootstrap-servers
security.protocol=SASL_SSL
sasl.mechanisms=PLAIN
sasl.username=your-kafka-api-key
sasl.password=your-kafka-api-secret
EOF
    echo -e "${YELLOW}⚠️  Please edit client.properties with your actual Kafka credentials${NC}"
    echo -e "${YELLOW}   - Get credentials from: https://confluent.cloud/environments${NC}"
else
    echo -e "${GREEN}✅ client.properties file found${NC}"
fi

# Check if Docker is running (for local testing)
if command -v docker &> /dev/null; then
    if docker info >/dev/null 2>&1; then
        echo -e "${GREEN}✅ Docker is running${NC}"
    else
        echo -e "${YELLOW}⚠️  Docker is installed but not running${NC}"
        echo -e "${YELLOW}   Start Docker if you want to test locally first${NC}"
    fi
else
    echo -e "${YELLOW}⚠️  Docker not found (optional for cloud deployment)${NC}"
fi

# Set up gcloud configuration for the project
echo -e "${YELLOW}🔧 Configuring gcloud for deployment...${NC}"
gcloud config set run/region us-central1
gcloud config set run/platform managed

echo ""
echo -e "${GREEN}🎉 Environment setup complete!${NC}"
echo "================================"
echo -e "${BLUE}Project ID:${NC} $PROJECT_ID"
echo -e "${BLUE}Region:${NC} us-central1"
echo ""
echo -e "${YELLOW}📋 Next Steps:${NC}"
echo "1. Edit .env file with your API keys (if not done already)"
echo "2. Edit client.properties with your Kafka credentials (if not done already)"
echo "3. Run: ./deploy.sh"
echo ""
echo -e "${GREEN}✅ Ready for deployment!${NC}"
