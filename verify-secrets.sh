#!/bin/bash

# Script to verify Google Cloud secrets are properly configured
# Run this before deploying to ensure all secrets exist and are accessible

PROJECT_ID="563072551472"
REGION="us-central1"

echo "=========================================="
echo "Verifying Google Cloud Secrets"
echo "=========================================="
echo ""

# Check if gcloud is installed
if ! command -v gcloud &> /dev/null; then
    echo "❌ ERROR: gcloud CLI not found. Please install it first."
    exit 1
fi

# Set project
echo "Setting project to: $PROJECT_ID"
gcloud config set project $PROJECT_ID
echo ""

# List all secrets
echo "📋 Listing all secrets in project..."
gcloud secrets list --project=$PROJECT_ID
echo ""

# Check each required secret
SECRETS=("gemini-api-key" "elevenlabs-api-key" "kafka-client-properties")

for SECRET in "${SECRETS[@]}"; do
    echo "----------------------------------------"
    echo "Checking secret: $SECRET"
    echo "----------------------------------------"
    
    # Check if secret exists
    if gcloud secrets describe $SECRET --project=$PROJECT_ID &> /dev/null; then
        echo "✅ Secret exists: $SECRET"
        
        # Get secret metadata
        echo "📝 Secret metadata:"
        gcloud secrets describe $SECRET --project=$PROJECT_ID --format="table(name,createTime,replication.automatic)"
        
        # Check if we can access the latest version
        if gcloud secrets versions access latest --secret=$SECRET --project=$PROJECT_ID &> /dev/null; then
            echo "✅ Can access latest version"
            
            # For kafka-client-properties, show first few lines
            if [ "$SECRET" == "kafka-client-properties" ]; then
                echo ""
                echo "📄 First 3 lines of kafka-client-properties:"
                gcloud secrets versions access latest --secret=$SECRET --project=$PROJECT_ID | head -n 3
                echo ""
                
                # Verify it contains required fields
                CONTENT=$(gcloud secrets versions access latest --secret=$SECRET --project=$PROJECT_ID)
                
                if echo "$CONTENT" | grep -q "bootstrap.servers"; then
                    echo "✅ Contains bootstrap.servers"
                else
                    echo "❌ Missing bootstrap.servers"
                fi
                
                if echo "$CONTENT" | grep -q "sasl.username"; then
                    echo "✅ Contains sasl.username"
                else
                    echo "❌ Missing sasl.username"
                fi
                
                if echo "$CONTENT" | grep -q "sasl.password"; then
                    echo "✅ Contains sasl.password"
                else
                    echo "❌ Missing sasl.password"
                fi
            else
                # For API keys, just show length
                LENGTH=$(gcloud secrets versions access latest --secret=$SECRET --project=$PROJECT_ID | wc -c)
                echo "📏 Secret length: $LENGTH characters"
            fi
        else
            echo "❌ Cannot access latest version - check permissions"
        fi
    else
        echo "❌ Secret does NOT exist: $SECRET"
        echo "   Create it with: gcloud secrets create $SECRET --project=$PROJECT_ID"
    fi
    echo ""
done

echo "=========================================="
echo "Checking Cloud Run Services"
echo "=========================================="
echo ""

# List Cloud Run services
echo "📋 Current Cloud Run services:"
gcloud run services list --project=$PROJECT_ID --region=$REGION --format="table(name,status,url)"
echo ""

# Check if services can access secrets
SERVICES=("chess-commentary-backend" "chess-commentary-consumer" "chess-commentary-producer")

for SERVICE in "${SERVICES[@]}"; do
    echo "----------------------------------------"
    echo "Checking service: $SERVICE"
    echo "----------------------------------------"
    
    if gcloud run services describe $SERVICE --project=$PROJECT_ID --region=$REGION &> /dev/null; then
        echo "✅ Service exists: $SERVICE"
        
        # Check service account
        SERVICE_ACCOUNT=$(gcloud run services describe $SERVICE --project=$PROJECT_ID --region=$REGION --format="value(spec.template.spec.serviceAccountName)")
        
        if [ -z "$SERVICE_ACCOUNT" ]; then
            SERVICE_ACCOUNT="default"
        fi
        
        echo "🔑 Service account: $SERVICE_ACCOUNT"
        
        # Note: Checking IAM permissions requires additional API calls
        echo "💡 Ensure this service account has 'Secret Manager Secret Accessor' role"
    else
        echo "⚠️  Service not deployed yet: $SERVICE"
    fi
    echo ""
done

echo "=========================================="
echo "Summary"
echo "=========================================="
echo ""
echo "✅ If all secrets exist and are accessible, you're ready to deploy!"
echo ""
echo "To deploy, run:"
echo "  gcloud builds submit --config=cloudbuild.yaml --project=$PROJECT_ID"
echo ""
echo "To view logs after deployment:"
echo "  gcloud run services logs read chess-commentary-consumer --project=$PROJECT_ID --region=$REGION --limit=100"
echo "  gcloud run services logs read chess-commentary-producer --project=$PROJECT_ID --region=$REGION --limit=100"
echo ""
