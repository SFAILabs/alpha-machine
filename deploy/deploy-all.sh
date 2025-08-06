#!/bin/bash

# Master Deployment Script for Alpha Machine
# Usage: ./deploy-all.sh [environment] [services...]

set -e

# Configuration
ENVIRONMENT="${1:-production}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
DEPLOY_SERVICE_SCRIPT="$SCRIPT_DIR/deploy-service.sh"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m'

# Default services to deploy (in order)
DEFAULT_SERVICES=("transcript" "linear" "notion" "slackbot")

# Parse services from command line or use defaults
if [ $# -gt 1 ]; then
    shift  # Remove environment parameter
    SERVICES=("$@")
else
    SERVICES=("${DEFAULT_SERVICES[@]}")
fi

echo -e "${BLUE}🚀 Alpha Machine Mass Deployment${NC}"
echo "======================================="
echo -e "${BLUE}Environment: ${YELLOW}$ENVIRONMENT${NC}"
echo -e "${BLUE}Services: ${YELLOW}${SERVICES[*]}${NC}"
echo ""

# Ensure we're in the project root
cd "$PROJECT_ROOT"

# Validate deploy-service.sh exists
if [ ! -f "$DEPLOY_SERVICE_SCRIPT" ]; then
    echo -e "${RED}❌ Error: deploy-service.sh not found at $DEPLOY_SERVICE_SCRIPT${NC}"
    exit 1
fi

# Make deploy-service.sh executable
chmod +x "$DEPLOY_SERVICE_SCRIPT"

# Track deployment results
declare -A DEPLOYMENT_RESULTS
declare -A SERVICE_URLS
SUCCESSFUL_DEPLOYMENTS=()
FAILED_DEPLOYMENTS=()

# Setup GCP project and APIs
echo -e "${BLUE}🔧 Setting up GCP environment...${NC}"
if [ -f .env ]; then
    export $(grep -v '^#' .env | grep -v '^$' | xargs)
fi

PROJECT_ID="${GCP_PROJECT_ID:-alpha-machine-468018}"
gcloud config set project $PROJECT_ID

# Enable required APIs
echo -e "${BLUE}📋 Enabling required GCP APIs...${NC}"
gcloud services enable \
    cloudbuild.googleapis.com \
    run.googleapis.com \
    artifactregistry.googleapis.com \
    --quiet

# Function to deploy a single service
deploy_service() {
    local service_name="$1"
    echo ""
    echo -e "${BLUE}🚀 Deploying $service_name...${NC}"
    echo "$(date '+%Y-%m-%d %H:%M:%S') - Starting deployment of $service_name" >> deploy.log
    
    if "$DEPLOY_SERVICE_SCRIPT" "$service_name" "$ENVIRONMENT" 2>&1 | tee -a "deploy-$service_name.log"; then
        DEPLOYMENT_RESULTS["$service_name"]="SUCCESS"
        SUCCESSFUL_DEPLOYMENTS+=("$service_name")
        
        # Extract service URL
        local service_url=$(gcloud run services describe "${service_name}-service" \
            --region=us-central1 \
            --format="value(status.url)" 2>/dev/null || echo "URL_NOT_FOUND")
        SERVICE_URLS["$service_name"]="$service_url"
        
        echo -e "${GREEN}✅ $service_name deployed successfully${NC}"
        echo "$(date '+%Y-%m-%d %H:%M:%S') - SUCCESS: $service_name deployed to $service_url" >> deploy.log
    else
        DEPLOYMENT_RESULTS["$service_name"]="FAILED"
        FAILED_DEPLOYMENTS+=("$service_name")
        echo -e "${RED}❌ $service_name deployment failed${NC}"
        echo "$(date '+%Y-%m-%d %H:%M:%S') - FAILED: $service_name deployment failed" >> deploy.log
        
        # Continue with other services rather than exiting
        echo -e "${YELLOW}⚠️  Continuing with remaining services...${NC}"
    fi
}

# Initialize deployment log
echo "Alpha Machine Deployment Log - $(date)" > deploy.log
echo "Environment: $ENVIRONMENT" >> deploy.log
echo "Services: ${SERVICES[*]}" >> deploy.log
echo "" >> deploy.log

# Deploy each service
for service in "${SERVICES[@]}"; do
    # Validate service exists
    if [ ! -d "services/$service" ]; then
        echo -e "${RED}❌ Service '$service' not found in services/ directory${NC}"
        DEPLOYMENT_RESULTS["$service"]="NOT_FOUND"
        FAILED_DEPLOYMENTS+=("$service")
        continue
    fi
    
    deploy_service "$service"
    
    # Small delay between deployments to avoid rate limits
    sleep 5
done

# Generate deployment summary
echo ""
echo -e "${BLUE}=================================================${NC}"
echo -e "${BLUE}🎯 DEPLOYMENT SUMMARY${NC}"
echo -e "${BLUE}=================================================${NC}"
echo -e "${BLUE}Environment: ${YELLOW}$ENVIRONMENT${NC}"
echo -e "${BLUE}Total Services: ${YELLOW}${#SERVICES[@]}${NC}"
echo -e "${GREEN}Successful: ${YELLOW}${#SUCCESSFUL_DEPLOYMENTS[@]}${NC}"
echo -e "${RED}Failed: ${YELLOW}${#FAILED_DEPLOYMENTS[@]}${NC}"
echo ""

if [ ${#SUCCESSFUL_DEPLOYMENTS[@]} -gt 0 ]; then
    echo -e "${GREEN}✅ SUCCESSFUL DEPLOYMENTS:${NC}"
    for service in "${SUCCESSFUL_DEPLOYMENTS[@]}"; do
        echo -e "${GREEN}  ✓ $service${NC} - ${SERVICE_URLS[$service]}"
    done
    echo ""
fi

if [ ${#FAILED_DEPLOYMENTS[@]} -gt 0 ]; then
    echo -e "${RED}❌ FAILED DEPLOYMENTS:${NC}"
    for service in "${FAILED_DEPLOYMENTS[@]}"; do
        echo -e "${RED}  ✗ $service${NC} - ${DEPLOYMENT_RESULTS[$service]}"
    done
    echo ""
    echo -e "${YELLOW}💡 Check individual logs: deploy-<service>.log${NC}"
fi

# Create deployment info file
cat > deployment-info.json << EOF
{
  "timestamp": "$(date -u +"%Y-%m-%dT%H:%M:%SZ")",
  "environment": "$ENVIRONMENT",
  "project_id": "$PROJECT_ID",
  "successful_deployments": [$(printf '"%s",' "${SUCCESSFUL_DEPLOYMENTS[@]}" | sed 's/,$//')]
  "failed_deployments": [$(printf '"%s",' "${FAILED_DEPLOYMENTS[@]}" | sed 's/,$//')]
  "service_urls": {
$(for service in "${SUCCESSFUL_DEPLOYMENTS[@]}"; do
    echo "    \"$service\": \"${SERVICE_URLS[$service]}\","
done | sed '$s/,$//')
  }
}
EOF

echo -e "${BLUE}📋 Deployment info saved to: deployment-info.json${NC}"

# Final status
if [ ${#FAILED_DEPLOYMENTS[@]} -eq 0 ]; then
    echo -e "${GREEN}🎉 ALL DEPLOYMENTS SUCCESSFUL!${NC}"
    exit 0
else
    echo -e "${YELLOW}⚠️  Some deployments failed. Check logs for details.${NC}"
    exit 1
fi 