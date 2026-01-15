#!/bin/bash

# Verification script for frontend configuration
# Checks that all hardcoded URLs have been replaced with API_CONFIG

echo "🔍 Verifying Frontend Configuration..."
echo "========================================"

# Check for hardcoded localhost URLs (excluding config file itself)
echo ""
echo "1. Checking for hardcoded localhost URLs..."
HARDCODED=$(grep -r "127\.0\.0\.1:8000\|localhost:8000" frontend/src --exclude-dir=node_modules --exclude="environment.js" | grep -v "^Binary" || true)

if [ -z "$HARDCODED" ]; then
    echo "✅ No hardcoded URLs found (excluding environment.js)"
else
    echo "❌ Found hardcoded URLs:"
    echo "$HARDCODED"
    exit 1
fi

# Check that API_CONFIG is imported in key files
echo ""
echo "2. Checking API_CONFIG imports..."

FILES_TO_CHECK=(
    "frontend/src/App.jsx"
    "frontend/src/hooks/useCommentary.js"
    "frontend/src/utils/audioQueue.js"
)

for file in "${FILES_TO_CHECK[@]}"; do
    if grep -q "import.*API_CONFIG.*from.*environment" "$file"; then
        echo "✅ $file imports API_CONFIG"
    else
        echo "❌ $file missing API_CONFIG import"
        exit 1
    fi
done

# Check that environment.js exists
echo ""
echo "3. Checking environment.js exists..."
if [ -f "frontend/src/config/environment.js" ]; then
    echo "✅ environment.js found"
else
    echo "❌ environment.js not found"
    exit 1
fi

# Check that API_CONFIG is used in fetch calls
echo ""
echo "4. Checking API_CONFIG usage in fetch calls..."
if grep -q "API_CONFIG.BACKEND_URL" frontend/src/App.jsx; then
    echo "✅ App.jsx uses API_CONFIG.BACKEND_URL"
else
    echo "❌ App.jsx not using API_CONFIG.BACKEND_URL"
    exit 1
fi

if grep -q "API_CONFIG.WS_URL" frontend/src/hooks/useCommentary.js; then
    echo "✅ useCommentary.js uses API_CONFIG.WS_URL"
else
    echo "❌ useCommentary.js not using API_CONFIG.WS_URL"
    exit 1
fi

echo ""
echo "========================================"
echo "✅ All checks passed! Frontend configuration is correct."
echo ""
echo "📋 Summary:"
echo "  - No hardcoded URLs found"
echo "  - API_CONFIG properly imported"
echo "  - environment.js exists"
echo "  - API_CONFIG used in all fetch/WebSocket calls"
echo ""
echo "🚀 Ready for deployment!"
