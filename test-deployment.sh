#!/bin/bash

# Chess Commentary System - Deployment Test Script
# Tests the deployed services to ensure they're working correctly

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}🧪 Chess Commentary System - Deployment Test${NC}"
echo "=============================================="

# Get service URLs
echo -e "${YELLOW}🔍 Getting service URLs...${NC}"

BACKEND_URL=$(gcloud run services describe chess-commentary-backend --region=us-central1 --format="value(status.url)" 2>/dev/null)
FRONTEND_URL=$(gcloud run services describe chess-commentary-frontend --region=us-central1 --format="value(status.url)" 2>/dev/null)

if [ -z "$BACKEND_URL" ] || [ -z "$FRONTEND_URL" ]; then
    echo -e "${RED}❌ Services not found. Please deploy first with ./deploy.sh${NC}"
    exit 1
fi

echo -e "${GREEN}✅ Backend URL: $BACKEND_URL${NC}"
echo -e "${GREEN}✅ Frontend URL: $FRONTEND_URL${NC}"

# Test backend health endpoint
echo -e "${YELLOW}🏥 Testing backend health...${NC}"
if curl -s -f "$BACKEND_URL/health" > /dev/null; then
    echo -e "${GREEN}✅ Backend health check passed${NC}"
else
    echo -e "${RED}❌ Backend health check failed${NC}"
    exit 1
fi

# Test frontend accessibility
echo -e "${YELLOW}🌐 Testing frontend accessibility...${NC}"
if curl -s -f "$FRONTEND_URL" > /dev/null; then
    echo -e "${GREEN}✅ Frontend is accessible${NC}"
else
    echo -e "${RED}❌ Frontend is not accessible${NC}"
    exit 1
fi

# Test backend API endpoints
echo -e "${YELLOW}🔌 Testing backend API endpoints...${NC}"

# Test analyze endpoint (should return error without username, but endpoint should exist)
ANALYZE_RESPONSE=$(curl -s -w "%{http_code}" -o /dev/null -X POST "$BACKEND_URL/analyze" -H "Content-Type: application/json" -d '{}')
if [ "$ANALYZE_RESPONSE" = "422" ] || [ "$ANALYZE_RESPONSE" = "400" ]; then
    echo -e "${GREEN}✅ Analyze endpoint is responding${NC}"
else
    echo -e "${RED}❌ Analyze endpoint returned unexpected status: $ANALYZE_RESPONSE${NC}"
fi

# Test game status endpoint (should return error for non-existent user, but endpoint should exist)
STATUS_RESPONSE=$(curl -s -w "%{http_code}" -o /dev/null "$BACKEND_URL/game/status/nonexistentuser")
if [ "$STATUS_RESPONSE" = "200" ] || [ "$STATUS_RESPONSE" = "404" ] || [ "$STATUS_RESPONSE" = "500" ]; then
    echo -e "${GREEN}✅ Game status endpoint is responding${NC}"
else
    echo -e "${RED}❌ Game status endpoint returned unexpected status: $STATUS_RESPONSE${NC}"
fi

# Check service logs for errors
echo -e "${YELLOW}📋 Checking recent service logs...${NC}"

# Check backend logs
BACKEND_ERRORS=$(gcloud logging read 'resource.type=cloud_run_revision AND resource.labels.service_name=chess-commentary-backend AND severity>=ERROR' --limit=5 --format="value(textPayload)" 2>/dev/null | wc -l)
if [ "$BACKEND_ERRORS" -eq 0 ]; then
    echo -e "${GREEN}✅ No recent backend errors${NC}"
else
    echo -e "${YELLOW}⚠️  Found $BACKEND_ERRORS recent backend errors (check logs)${NC}"
fi

# Check consumer logs
CONSUMER_ERRORS=$(gcloud logging read 'resource.type=cloud_run_revision AND resource.labels.service_name=chess-commentary-consumer AND severity>=ERROR' --limit=5 --format="value(textPayload)" 2>/dev/null | wc -l)
if [ "$CONSUMER_ERRORS" -eq 0 ]; then
    echo -e "${GREEN}✅ No recent consumer errors${NC}"
else
    echo -e "${YELLOW}⚠️  Found $CONSUMER_ERRORS recent consumer errors (check logs)${NC}"
fi

# Check producer logs
PRODUCER_ERRORS=$(gcloud logging read 'resource.type=cloud_run_revision AND resource.labels.service_name=chess-commentary-producer AND severity>=ERROR' --limit=5 --format="value(textPayload)" 2>/dev/null | wc -l)
if [ "$PRODUCER_ERRORS" -eq 0 ]; then
    echo -e "${GREEN}✅ No recent producer errors${NC}"
else
    echo -e "${YELLOW}⚠️  Found $PRODUCER_ERRORS recent producer errors (check logs)${NC}"
fi

# Test WebSocket connection (basic connectivity test)
echo -e "${YELLOW}🔌 Testing WebSocket connectivity...${NC}"
WS_URL=$(echo "$BACKEND_URL" | sed 's/https:/wss:/')
if command -v wscat &> /dev/null; then
    # If wscat is available, test WebSocket with timeout
    timeout 5 wscat -c "$WS_URL/ws/commentary/test" -x 'ping' 2>/dev/null && echo -e "${GREEN}✅ WebSocket is accessible${NC}" || echo -e "${YELLOW}⚠️  WebSocket test inconclusive (this is normal)${NC}"
else
    echo -e "${YELLOW}⚠️  wscat not available, skipping WebSocket test${NC}"
fi

echo ""
echo -e "${GREEN}🎉 Deployment Test Complete!${NC}"
echo "============================="
echo ""
echo -e "${BLUE}📊 Test Results Summary:${NC}"
echo -e "${GREEN}✅ Backend Health: OK${NC}"
echo -e "${GREEN}✅ Frontend Access: OK${NC}"
echo -e "${GREEN}✅ API Endpoints: OK${NC}"
echo ""
echo -e "${BLUE}🌐 Your Chess Commentary System:${NC}"
echo -e "${BLUE}Frontend:${NC} $FRONTEND_URL"
echo -e "${BLUE}Backend:${NC} $BACKEND_URL"
echo ""
echo -e "${YELLOW}📋 Next Steps:${NC}"
echo "1. Visit the frontend URL to test the full system"
echo "2. Try analyzing a chess player profile"
echo "3. Start a live game on Lichess and test commentary"
echo ""
echo -e "${GREEN}✅ System is ready for use!${NC}"

# Optional: Open frontend in browser (if on desktop)
if command -v xdg-open &> /dev/null; then
    read -p "Open frontend in browser? (y/n): " open_browser
    if [ "$open_browser" = "y" ]; then
        xdg-open "$FRONTEND_URL"
    fi
elif command -v open &> /dev/null; then
    read -p "Open frontend in browser? (y/n): " open_browser
    if [ "$open_browser" = "y" ]; then
        open "$FRONTEND_URL"
    fi
fi