# Chess Commentary System - Google Cloud Deployment Guide

This guide will help you deploy your chess commentary system to Google Cloud Run.

## Prerequisites

1. **Google Cloud Account**: You need a Google Cloud account with billing enabled
2. **Google Cloud CLI**: Install the `gcloud` CLI tool
3. **Docker**: Ensure Docker is installed (for local testing)
4. **API Keys**: Your ElevenLabs and Gemini API keys should be in `.env` file
5. **Kafka Configuration**: Your `client.properties` file should be present

## Quick Deployment (Recommended)

### Step 1: Setup Google Cloud Project

```bash
# Install Google Cloud CLI if not already installed
# https://cloud.google.com/sdk/docs/install

# Login to Google Cloud
gcloud auth login

# Create a new project (or use existing)
gcloud projects create chess-commentary-system --name="Chess Commentary System"

# Set the project
gcloud config set project chess-commentary-system

# Enable billing for the project (required for Cloud Run)
# Go to: https://console.cloud.google.com/billing
```

### Step 2: Run Automated Deployment

```bash
# Make the deployment script executable
chmod +x deploy.sh

# Run the deployment
./deploy.sh
```

The script will:
- ✅ Check and enable required Google Cloud APIs
- 🔐 Create secrets for your API keys
- 🏗️ Build and deploy all services using Cloud Build
- 🔧 Configure the frontend with cloud URLs
- 📋 Provide you with the final URLs

### Step 3: Access Your System

After deployment completes, you'll get:
- **Frontend URL**: `https://chess-commentary-frontend-XXXXX-uc.a.run.app`
- **Backend URL**: `https://chess-commentary-backend-XXXXX-uc.a.run.app`

## Manual Deployment (Advanced)

If you prefer manual control or the automated script fails:

### 1. Enable Required APIs

```bash
gcloud services enable cloudbuild.googleapis.com
gcloud services enable run.googleapis.com
gcloud services enable secretmanager.googleapis.com
gcloud services enable containerregistry.googleapis.com
```

### 2. Create Secrets

```bash
# Create API key secrets
echo -n "YOUR_ELEVENLABS_KEY" | gcloud secrets create elevenlabs-api-key --data-file=-
echo -n "YOUR_GEMINI_KEY" | gcloud secrets create gemini-api-key --data-file=-

# Create Kafka config secret
gcloud secrets create kafka-client-properties --data-file=client.properties
```

### 3. Build and Deploy with Cloud Build

```bash
# Submit build
gcloud builds submit --config cloudbuild.yaml .
```

### 4. Update Frontend Configuration

After deployment, update the frontend to use the cloud backend URL:

```bash
# Get backend URL
BACKEND_URL=$(gcloud run services describe chess-commentary-backend --region=us-central1 --format="value(status.url)")

# Update frontend configuration
sed -i "s|YOUR_HASH|$(echo $BACKEND_URL | cut -d'/' -f3 | cut -d'-' -f4)|g" frontend/src/config/environment.js

# Rebuild and redeploy frontend
gcloud builds submit --config - . << EOF
steps:
  - name: 'gcr.io/cloud-builders/docker'
    args: ['build', '-t', 'gcr.io/$PROJECT_ID/chess-commentary-frontend:updated', '-f', 'Dockerfile.frontend', '.']
  - name: 'gcr.io/cloud-builders/docker'
    args: ['push', 'gcr.io/$PROJECT_ID/chess-commentary-frontend:updated']
  - name: 'gcr.io/cloud-builders/gcloud'
    args: ['run', 'deploy', 'chess-commentary-frontend', '--image', 'gcr.io/$PROJECT_ID/chess-commentary-frontend:updated', '--region', 'us-central1']
EOF
```

## Architecture Overview

Your deployed system will have:

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Frontend      │    │    Backend      │    │   Consumer      │
│  (Cloud Run)    │◄──►│  (Cloud Run)    │◄──►│  (Cloud Run)    │
│                 │    │                 │    │                 │
│ React App       │    │ FastAPI + WS    │    │ Commentary Gen  │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                                │                        │
                                ▼                        ▼
                       ┌─────────────────┐    ┌─────────────────┐
                       │   Producer      │    │     Kafka       │
                       │  (Cloud Run)    │◄──►│   (Confluent)   │
                       │                 │    │                 │
                       │ Lichess Polling │    │   Streaming     │
                       └─────────────────┘    └─────────────────┘
```

## Service Details

### Frontend Service
- **URL**: Public, accessible to users
- **Resources**: 512Mi RAM, 1 CPU
- **Scaling**: 0-5 instances
- **Purpose**: React app for user interface

### Backend Service  
- **URL**: Public, handles API requests
- **Resources**: 2Gi RAM, 2 CPU
- **Scaling**: 1-10 instances
- **Purpose**: FastAPI server with WebSocket support

### Consumer Service
- **URL**: Internal only
- **Resources**: 1Gi RAM, 1 CPU  
- **Scaling**: 1-3 instances
- **Purpose**: Generates AI commentary from moves

### Producer Service
- **URL**: Internal only
- **Resources**: 1Gi RAM, 1 CPU
- **Scaling**: 1-3 instances  
- **Purpose**: Polls Lichess API for live moves

## Monitoring and Logs

### View Logs
```bash
# All services
gcloud logging read 'resource.type=cloud_run_revision'

# Specific service
gcloud logging read 'resource.type=cloud_run_revision AND resource.labels.service_name=chess-commentary-backend'
```

### Monitor Performance
```bash
# Service status
gcloud run services list --region=us-central1

# Service details
gcloud run services describe chess-commentary-backend --region=us-central1
```

## Scaling and Costs

### Expected Costs (Approximate)
- **Frontend**: ~$5-10/month (minimal usage)
- **Backend**: ~$20-50/month (depends on usage)
- **Consumer**: ~$15-30/month (continuous running)
- **Producer**: ~$15-30/month (continuous running)

**Total**: ~$55-120/month for moderate usage

### Cost Optimization
- Services auto-scale to zero when not in use (except consumer/producer)
- Use `--min-instances=0` for development environments
- Monitor usage in Google Cloud Console

## Troubleshooting

### Common Issues

1. **Build Failures**
   ```bash
   # Check build logs
   gcloud builds list --limit=5
   gcloud builds log BUILD_ID
   ```

2. **Service Not Starting**
   ```bash
   # Check service logs
   gcloud logging read 'resource.type=cloud_run_revision AND resource.labels.service_name=SERVICE_NAME' --limit=50
   ```

3. **WebSocket Connection Issues**
   - Ensure backend service allows WebSocket connections
   - Check CORS configuration in `backend/main.py`

4. **API Key Issues**
   ```bash
   # Verify secrets exist
   gcloud secrets list
   
   # Check secret values (be careful!)
   gcloud secrets versions access latest --secret=elevenlabs-api-key
   ```

### Getting Help

1. **Check service status**: Google Cloud Console → Cloud Run
2. **View logs**: Google Cloud Console → Logging
3. **Monitor metrics**: Google Cloud Console → Monitoring

## Security Notes

- API keys are stored as Google Cloud Secrets
- Services use IAM for authentication
- Frontend and backend are publicly accessible (as needed)
- Consumer and producer are internal-only
- All traffic uses HTTPS/WSS in production

## Next Steps

After successful deployment:

1. **Test the system** with a live chess game
2. **Monitor performance** and adjust scaling if needed
3. **Set up alerts** for service failures
4. **Consider CDN** for better global performance
5. **Implement CI/CD** for automated deployments

Your chess commentary system is now running on Google Cloud! 🎉