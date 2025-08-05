#!/bin/bash

# Load environment variables from .env file
if [ -f .env ]; then
    echo "Loading environment variables from .env file..."
    export $(grep -v '^#' .env | xargs)
else
    echo "Warning: .env file not found. Using environment variables only."
fi

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration
PROJECT_ID=${GCP_PROJECT_ID:-"your-project-id"}
REGION="us-central1"
SERVICES=("transcript" "slackbot" "linear" "notion")

echo "--- Deploying Alpha Machine to Google Cloud Run ---"

# Function to get the correct port for each service
get_service_port() {
    case $1 in
        "transcript") echo "8000" ;;
        "slackbot") echo "8001" ;;
        "linear") echo "8002" ;;
        "notion") echo "8003" ;;
        *) echo "8000" ;;
    esac
}

# Function to create or update a secret
create_or_update_secret() {
    local secret_name=$1
    local secret_value=$2
    
    if [ -z "$secret_value" ] || [ "$secret_value" = "your-secret-here" ] || [ "$secret_value" = "dummy" ]; then
        echo -e "${YELLOW}⚠️  Skipping $secret_name - no value provided${NC}"
        return 1
    fi
    
    # Check if secret exists
    if gcloud secrets describe $secret_name --project=$PROJECT_ID >/dev/null 2>&1; then
        echo "Updating existing secret: $secret_name"
        echo -n "$secret_value" | gcloud secrets versions add $secret_name --data-file=-
    else
        echo "Creating new secret: $secret_name"
        echo -n "$secret_value" | gcloud secrets create $secret_name --data-file=-
    fi
}

echo -e "${BLUE}🚀 Alpha Machine Cloud Run Deployment${NC}"
echo "======================================="

echo -e "${BLUE}📋 Setting GCP project to: $PROJECT_ID${NC}"
gcloud config set project $PROJECT_ID

echo -e "${BLUE}🔧 Enabling required APIs...${NC}"
gcloud services enable cloudbuild.googleapis.com
gcloud services enable run.googleapis.com
gcloud services enable containerregistry.googleapis.com
gcloud services enable artifactregistry.googleapis.com
gcloud services enable secretmanager.googleapis.com

echo -e "${BLUE}🔐 Creating/updating secrets...${NC}"
create_or_update_secret "openai-api-key" "$OPENAI_API_KEY"
create_or_update_secret "linear-api-key" "$LINEAR_API_KEY"
create_or_update_secret "supabase-service-role-key" "$SUPABASE_SERVICE_ROLE_KEY"
create_or_update_secret "slack-bot-token" "$SLACK_BOT_TOKEN"
create_or_update_secret "slack-signing-secret" "$SLACK_SIGNING_SECRET"
create_or_update_secret "notion-token" "$NOTION_TOKEN"

# Collect service URLs for later output
SERVICE_URLS=()

# Deploy each service
for service in "${SERVICES[@]}"; do
    echo -e "${BLUE}🏗️  Building and deploying $service service...${NC}"
    
    # Build from workspace root using service-specific Dockerfile
    echo "Building container image for $service from workspace root..."
    gcloud builds submit --tag us-central1-docker.pkg.dev/$PROJECT_ID/alpha-machine/$service-service -f ./services/$service/Dockerfile .
    
    # Prepare environment variables (including what used to be secrets)
    ENV_VARS="ENVIRONMENT=production"
    ENV_VARS="$ENV_VARS,OPENAI_MODEL=${OPENAI_MODEL:-gpt-4.1-mini}"
    ENV_VARS="$ENV_VARS,OPENAI_MAX_TOKENS=${OPENAI_MAX_TOKENS:-20000}"
    ENV_VARS="$ENV_VARS,OPENAI_TEMPERATURE=${OPENAI_TEMPERATURE:-0.4}"
    ENV_VARS="$ENV_VARS,LINEAR_TEAM_NAME=${LINEAR_TEAM_NAME:-Jonathan}"
    ENV_VARS="$ENV_VARS,LINEAR_TEST_MODE=${LINEAR_TEST_MODE:-true}"
    ENV_VARS="$ENV_VARS,NEXT_PUBLIC_SUPABASE_URL=${NEXT_PUBLIC_SUPABASE_URL:-}"
    ENV_VARS="$ENV_VARS,GCP_PROJECT_ID=$PROJECT_ID"
    ENV_VARS="$ENV_VARS,GCP_REGION=$REGION"
    
    # Add API keys and secrets as environment variables (much simpler than secret mounting)
    if [ ! -z "$OPENAI_API_KEY" ] && [ "$OPENAI_API_KEY" != "your-secret-here" ]; then
        ENV_VARS="$ENV_VARS,OPENAI_API_KEY=$OPENAI_API_KEY"
    fi
    if [ ! -z "$LINEAR_API_KEY" ] && [ "$LINEAR_API_KEY" != "your-secret-here" ]; then
        ENV_VARS="$ENV_VARS,LINEAR_API_KEY=$LINEAR_API_KEY"
    fi
    if [ ! -z "$SUPABASE_SERVICE_ROLE_KEY" ] && [ "$SUPABASE_SERVICE_ROLE_KEY" != "your-secret-here" ]; then
        ENV_VARS="$ENV_VARS,SUPABASE_SERVICE_ROLE_KEY=$SUPABASE_SERVICE_ROLE_KEY"
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
    
    # Deploy to Cloud Run (simplified - no secrets, just environment variables)
    gcloud run deploy $service-service \
        --image us-central1-docker.pkg.dev/$PROJECT_ID/alpha-machine/$service-service \
        --platform managed \
        --region $REGION \
        --allow-unauthenticated \
        --port $(get_service_port $service) \
        --memory 1Gi \
        --cpu 1 \
        --max-instances 10 \
        --timeout 300s \
        --set-env-vars "$ENV_VARS"
    
    # Ensure public access by setting IAM policy
    gcloud beta run services add-iam-policy-binding $service-service \
        --region=$REGION \
        --member="allUsers" \
        --role="roles/run.invoker" \
        --quiet
    
    echo -e "${GREEN}✅ $service service deployed successfully${NC}"
    
    # Get service URL
    SERVICE_URL=$(gcloud run services describe $service-service --region=$REGION --format='value(status.url)')
    SERVICE_URLS+=("$service: $SERVICE_URL")
done

echo -e "${GREEN}🎉 All services deployed successfully!${NC}"
echo "========================================="
echo -e "${BLUE}📍 Service URLs:${NC}"
for url in "${SERVICE_URLS[@]}"; do
    echo "  $url"
done
echo ""
echo -e "${YELLOW}💡 Next steps:${NC}"
echo "1. Update your .env file with the Cloud Run URLs above"
echo "2. Configure webhook URLs in your Slack app to point to the slackbot-service"
echo "3. Test the services using the health endpoints (add /health to any URL)" 