#!/bin/bash

# Individual Service Deployment Script
# Usage: ./deploy-service.sh <service-name> [environment]

set -e  # Exit on any error

# Configuration
SERVICE_NAME="$1"
ENVIRONMENT="${2:-production}"
PROJECT_ID="${GCP_PROJECT_ID:-alpha-machine-468018}"
REGION="us-central1"
REGISTRY="us-central1-docker.pkg.dev"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Validate inputs
if [ -z "$SERVICE_NAME" ]; then
    echo -e "${RED}❌ Error: Service name is required${NC}"
    echo "Usage: $0 <service-name> [environment]"
    echo "Available services: transcript, slackbot, linear, notion"
    exit 1
fi

# Validate service exists
if [ ! -d "services/$SERVICE_NAME" ]; then
    echo -e "${RED}❌ Error: Service 'services/$SERVICE_NAME' not found${NC}"
    exit 1
fi

# Validate Dockerfile exists
if [ ! -f "services/$SERVICE_NAME/Dockerfile" ]; then
    echo -e "${RED}❌ Error: Dockerfile not found at 'services/$SERVICE_NAME/Dockerfile'${NC}"
    exit 1
fi

echo -e "${BLUE}🚀 Deploying $SERVICE_NAME service to $ENVIRONMENT environment${NC}"
echo "=================================================="

# Load environment variables
if [ -f .env ]; then
    echo -e "${GREEN}📋 Loading environment variables from .env${NC}"
    export $(grep -v '^#' .env | grep -v '^$' | xargs)
else
    echo -e "${YELLOW}⚠️  Warning: .env file not found${NC}"
fi

# Set GCP project
echo -e "${BLUE}📋 Setting GCP project to: $PROJECT_ID${NC}"
gcloud config set project $PROJECT_ID

# Get service port
get_service_port() {
    case $1 in
        "transcript") echo "8000" ;;
        "slackbot") echo "8001" ;;
        "linear") echo "8002" ;;
        "notion") echo "8003" ;;
        *) echo "8000" ;;
    esac
}

SERVICE_PORT=$(get_service_port $SERVICE_NAME)
IMAGE_NAME="$REGISTRY/$PROJECT_ID/alpha-machine/$SERVICE_NAME-service"
SERVICE_FULL_NAME="$SERVICE_NAME-service"

# Create Cloud Build configuration
echo -e "${BLUE}🏗️  Creating Cloud Build configuration for $SERVICE_NAME${NC}"
cat > "/tmp/cloudbuild-$SERVICE_NAME.yaml" << EOF
steps:
- name: 'gcr.io/cloud-builders/docker'
  args: 
    - 'build'
    - '-f'
    - './services/$SERVICE_NAME/Dockerfile'
    - '-t'
    - '$IMAGE_NAME'
    - '.'
  timeout: '1200s'
images:
- '$IMAGE_NAME'
options:
  machineType: 'E2_HIGHCPU_8'
  diskSizeGb: 100
timeout: '1800s'
EOF

# Build the container
echo -e "${BLUE}🔨 Building container image for $SERVICE_NAME${NC}"
if ! gcloud builds submit --config "/tmp/cloudbuild-$SERVICE_NAME.yaml" . --timeout=1800s; then
    echo -e "${RED}❌ Build failed for $SERVICE_NAME${NC}"
    rm -f "/tmp/cloudbuild-$SERVICE_NAME.yaml"
    exit 1
fi

# Clean up build config
rm -f "/tmp/cloudbuild-$SERVICE_NAME.yaml"

# Prepare environment variables
echo -e "${BLUE}⚙️  Preparing environment variables${NC}"
ENV_VARS="ENVIRONMENT=$ENVIRONMENT"
ENV_VARS="$ENV_VARS,SERVICE_NAME=$SERVICE_NAME"
ENV_VARS="$ENV_VARS,OPENAI_MODEL=${OPENAI_MODEL:-gpt-4o-mini}"
ENV_VARS="$ENV_VARS,OPENAI_MAX_TOKENS=${OPENAI_MAX_TOKENS:-4000}"
ENV_VARS="$ENV_VARS,OPENAI_TEMPERATURE=${OPENAI_TEMPERATURE:-0.4}"
ENV_VARS="$ENV_VARS,LINEAR_TEAM_NAME=${LINEAR_TEAM_NAME:-Jonathan}"
ENV_VARS="$ENV_VARS,LINEAR_TEST_MODE=${LINEAR_TEST_MODE:-true}"
ENV_VARS="$ENV_VARS,GCP_PROJECT_ID=$PROJECT_ID"
ENV_VARS="$ENV_VARS,GCP_REGION=$REGION"

# Add API keys if available
if [ ! -z "$OPENAI_API_KEY" ] && [ "$OPENAI_API_KEY" != "your-secret-here" ]; then
    ENV_VARS="$ENV_VARS,OPENAI_API_KEY=$OPENAI_API_KEY"
fi
if [ ! -z "$LINEAR_API_KEY" ] && [ "$LINEAR_API_KEY" != "your-secret-here" ]; then
    ENV_VARS="$ENV_VARS,LINEAR_API_KEY=$LINEAR_API_KEY"
fi
if [ ! -z "$SUPABASE_SERVICE_ROLE_KEY" ] && [ "$SUPABASE_SERVICE_ROLE_KEY" != "your-secret-here" ]; then
    ENV_VARS="$ENV_VARS,SUPABASE_SERVICE_ROLE_KEY=$SUPABASE_SERVICE_ROLE_KEY"
fi
if [ ! -z "$NEXT_PUBLIC_SUPABASE_URL" ] && [ "$NEXT_PUBLIC_SUPABASE_URL" != "your-secret-here" ]; then
    ENV_VARS="$ENV_VARS,NEXT_PUBLIC_SUPABASE_URL=$NEXT_PUBLIC_SUPABASE_URL"
fi
if [ ! -z "$SLACK_BOT_TOKEN" ] && [ "$SLACK_BOT_TOKEN" != "your-secret-here" ]; then
    ENV_VARS="$ENV_VARS,SLACK_BOT_TOKEN=$SLACK_BOT_TOKEN"
fi
if [ ! -z "$SLACK_SIGNING_SECRET" ] && [ "$SLACK_SIGNING_SECRET" != "your-secret-here" ]; then
    ENV_VARS="$ENV_VARS,SLACK_SIGNING_SECRET=$SLACK_SIGNING_SECRET"
fi
if [ ! -z "$NOTION_TOKEN" ] && [ "$NOTION_TOKEN" != "your-secret-here" ]; then
    ENV_VARS="$ENV_VARS,NOTION_TOKEN=$NOTION_TOKEN"
fi

# Deploy to Cloud Run
echo -e "${BLUE}🚀 Deploying $SERVICE_NAME to Cloud Run${NC}"

# Check if service exists to determine deployment strategy
if gcloud run services describe $SERVICE_FULL_NAME --region=$REGION --project=$PROJECT_ID >/dev/null 2>&1; then
    echo -e "${YELLOW}📝 Service exists, updating...${NC}"
    DEPLOY_CMD="gcloud run deploy $SERVICE_FULL_NAME"
else
    echo -e "${GREEN}✨ Creating new service...${NC}"
    DEPLOY_CMD="gcloud run deploy $SERVICE_FULL_NAME"
fi

# Execute deployment
if ! $DEPLOY_CMD \
    --image $IMAGE_NAME \
    --platform managed \
    --region $REGION \
    --allow-unauthenticated \
    --port $SERVICE_PORT \
    --memory 1Gi \
    --cpu 1 \
    --max-instances 10 \
    --timeout 300s \
    --set-env-vars "$ENV_VARS" \
    --quiet; then
    
    echo -e "${YELLOW}⚠️  Standard deployment failed, trying with update strategy${NC}"
    
    # Try with update strategy for existing services
    if ! gcloud run deploy $SERVICE_FULL_NAME \
        --image $IMAGE_NAME \
        --platform managed \
        --region $REGION \
        --allow-unauthenticated \
        --port $SERVICE_PORT \
        --memory 1Gi \
        --cpu 1 \
        --max-instances 10 \
        --timeout 300s \
        --update-env-vars "$ENV_VARS" \
        --quiet; then
        
        echo -e "${RED}❌ Both deployment strategies failed for $SERVICE_NAME${NC}"
        exit 1
    fi
fi

# Set IAM policy for public access
echo -e "${BLUE}🔐 Setting IAM policy for public access${NC}"
gcloud run services add-iam-policy-binding $SERVICE_FULL_NAME \
    --region=$REGION \
    --member="allUsers" \
    --role="roles/run.invoker" \
    --quiet

# Get service URL
SERVICE_URL=$(gcloud run services describe $SERVICE_FULL_NAME --region=$REGION --format="value(status.url)")

echo -e "${GREEN}✅ $SERVICE_NAME service deployed successfully!${NC}"
echo -e "${GREEN}🌐 Service URL: $SERVICE_URL${NC}"

# Test the service
echo -e "${BLUE}🧪 Testing service health...${NC}"
if curl -f -s "$SERVICE_URL/health" >/dev/null 2>&1; then
    echo -e "${GREEN}✅ Health check passed${NC}"
elif curl -f -s "$SERVICE_URL/" >/dev/null 2>&1; then
    echo -e "${GREEN}✅ Service is responding${NC}"
else
    echo -e "${YELLOW}⚠️  Health check failed, but service may still be starting up${NC}"
fi

echo ""
echo -e "${GREEN}🎉 Deployment complete for $SERVICE_NAME!${NC}"
echo -e "${BLUE}📍 Service URL: $SERVICE_URL${NC}" 