#!/bin/bash

# Chess Commentary System - Google Cloud Deployment Script
# This script sets up and deploys the entire system to Google Cloud

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}🚀 Chess Commentary System - Google Cloud Deployment${NC}"
echo "=================================================="

# Check if gcloud is installed
if ! command -v gcloud &> /dev/null; then
    echo -e "${RED}❌ Google Cloud CLI not found. Please install it first:${NC}"
    echo "https://cloud.google.com/sdk/docs/install"
    exit 1
fi

# Get project ID
PROJECT_ID=$(gcloud config get-value project 2>/dev/null)
if [ -z "$PROJECT_ID" ]; then
    echo -e "${RED}❌ No Google Cloud project set. Please run:${NC}"
    echo "gcloud config set project YOUR_PROJECT_ID"
    exit 1
fi

echo -e "${GREEN}✅ Using Google Cloud Project: ${PROJECT_ID}${NC}"

# Check if required APIs are enabled
echo -e "${YELLOW}🔍 Checking required APIs...${NC}"
REQUIRED_APIS=(
    "cloudbuild.googleapis.com"
    "run.googleapis.com"
    "secretmanager.googleapis.com"
    "containerregistry.googleapis.com"
)

for api in "${REQUIRED_APIS[@]}"; do
    if gcloud services list --enabled --filter="name:$api" --format="value(name)" | grep -q "$api"; then
        echo -e "${GREEN}✅ $api is enabled${NC}"
    else
        echo -e "${YELLOW}⚠️  Enabling $api...${NC}"
        gcloud services enable "$api"
    fi
done

# Create secrets for API keys
echo -e "${YELLOW}🔐 Setting up secrets...${NC}"

# Check if .env file exists
if [ ! -f ".env" ]; then
    echo -e "${RED}❌ .env file not found. Please create it with your API keys.${NC}"
    exit 1
fi

# Read API keys from .env file
source .env

# Create secrets
echo -e "${YELLOW}📝 Creating ElevenLabs API key secret...${NC}"
echo -n "$ELEVENLABS_API_KEY" | gcloud secrets create elevenlabs-api-key --data-file=- --replication-policy="automatic" 2>/dev/null || \
echo -n "$ELEVENLABS_API_KEY" | gcloud secrets versions add elevenlabs-api-key --data-file=-

echo -e "${YELLOW}📝 Creating Gemini API key secret...${NC}"
echo -n "$GEMINI_API_KEY" | gcloud secrets create gemini-api-key --data-file=- --replication-policy="automatic" 2>/dev/null || \
echo -n "$GEMINI_API_KEY" | gcloud secrets versions add gemini-api-key --data-file=-

# Create Kafka config secret
echo -e "${YELLOW}📝 Creating Kafka config secret...${NC}"
if [ -f "client.properties" ]; then
    gcloud secrets create kafka-client-properties --data-file=client.properties --replication-policy="automatic" 2>/dev/null || \
    gcloud secrets versions add kafka-client-properties --data-file=client.properties
else
    echo -e "${RED}❌ client.properties file not found. Please ensure your Kafka config is available.${NC}"
    exit 1
fi

# Build and deploy using Cloud Build
echo -e "${YELLOW}🏗️  Starting Cloud Build deployment...${NC}"
gcloud builds submit --config cloudbuild.yaml .

# Get service URLs
echo -e "${YELLOW}🔍 Getting service URLs...${NC}"
BACKEND_URL=$(gcloud run services describe chess-commentary-backend --region=us-central1 --format="value(status.url)")
FRONTEND_URL=$(gcloud run services describe chess-commentary-frontend --region=us-central1 --format="value(status.url)")

echo ""
echo -e "${GREEN}🎉 Deployment Complete!${NC}"
echo "========================"
echo -e "${BLUE}Frontend URL:${NC} $FRONTEND_URL"
echo -e "${BLUE}Backend URL:${NC} $BACKEND_URL"
echo ""
echo -e "${YELLOW}📋 Next Steps:${NC}"
echo "1. Visit the frontend URL to access your chess commentary system"
echo "2. The system will automatically scale based on usage"
echo "3. Monitor logs with: gcloud logging read 'resource.type=cloud_run_revision'"
echo ""
echo -e "${GREEN}✅ Your chess commentary system is now live on Google Cloud!${NC}"