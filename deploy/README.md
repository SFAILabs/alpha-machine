# 🚀 Alpha Machine Deployment System

This directory contains robust deployment scripts for the Alpha Machine services to Google Cloud Platform.

## 📁 Files Overview

- **`deploy-service.sh`** - Individual service deployment with error handling
- **`deploy-all.sh`** - Mass deployment orchestrator with logging
- **`README.md`** - This documentation

## 🔧 Prerequisites

1. **Google Cloud SDK** installed and configured
2. **Docker** installed (for local testing)
3. **Environment file** (`.env`) in project root with required variables
4. **GCP Project** with billing enabled

### Required Environment Variables

```bash
# .env file in project root
GCP_PROJECT_ID=your-project-id
OPENAI_API_KEY=your-openai-key
LINEAR_API_KEY=your-linear-key
SUPABASE_SERVICE_ROLE_KEY=your-supabase-key
NEXT_PUBLIC_SUPABASE_URL=your-supabase-url
SLACK_BOT_TOKEN=xoxb-your-slack-token
SLACK_SIGNING_SECRET=your-slack-signing-secret
NOTION_TOKEN=your-notion-token
```

## 🚀 Quick Start

### Deploy All Services
```bash
cd alpha-machine
./deploy/deploy-all.sh
```

### Deploy Single Service
```bash
cd alpha-machine
./deploy/deploy-service.sh slackbot
```

### Deploy to Staging
```bash
./deploy/deploy-all.sh staging
```

### Deploy Specific Services
```bash
./deploy/deploy-all.sh production slackbot linear
```

## 📋 Available Services

| Service | Port | Description |
|---------|------|-------------|
| `transcript` | 8000 | Transcript processing service |
| `slackbot` | 8001 | Slack bot with AI integration |
| `linear` | 8002 | Linear project management integration |
| `notion` | 8003 | Notion workspace integration |

## 🛠️ Advanced Usage

### Individual Service Deployment

The `deploy-service.sh` script provides robust deployment for individual services:

```bash
# Deploy slackbot to production
./deploy/deploy-service.sh slackbot production

# Deploy with validation
./deploy/deploy-service.sh slackbot && curl -f https://your-service-url/health
```

**Features:**
- ✅ Comprehensive error handling
- ✅ Cloud Build configuration generation
- ✅ Environment variable validation
- ✅ Automatic health checks
- ✅ Fallback deployment strategies
- ✅ Service URL extraction

### Mass Deployment

The `deploy-all.sh` script orchestrates deployment of multiple services:

```bash
# Deploy all services
./deploy/deploy-all.sh

# Deploy to staging environment
./deploy/deploy-all.sh staging

# Deploy only core services
./deploy/deploy-all.sh production slackbot linear
```

**Features:**
- ✅ Parallel deployment tracking
- ✅ Detailed logging per service
- ✅ Deployment summary reports
- ✅ JSON deployment manifest
- ✅ Graceful failure handling
- ✅ Service URL collection

## 📊 Deployment Monitoring

### Logs
- **`deploy.log`** - Master deployment log
- **`deploy-<service>.log`** - Individual service logs
- **`deployment-info.json`** - JSON deployment manifest

### Example deployment-info.json
```json
{
  "timestamp": "2024-01-15T14:30:00Z",
  "environment": "production",
  "project_id": "alpha-machine-468018",
  "successful_deployments": ["slackbot", "linear"],
  "failed_deployments": ["notion"],
  "service_urls": {
    "slackbot": "https://slackbot-service-xxx.us-central1.run.app",
    "linear": "https://linear-service-xxx.us-central1.run.app"
  }
}
```

## 🔍 Troubleshooting

### Common Issues

#### 1. Build Failures
**Error:** `COPY failed: file not found`
**Solution:** Ensure Dockerfiles use monorepo structure
```dockerfile
# ✅ Correct
COPY . .
CMD ["uv", "run", "uvicorn", "services.myservice.main:app"]

# ❌ Wrong
COPY src/ /app/src
CMD ["uvicorn", "src.main:app"]
```

#### 2. Environment Variable Conflicts
**Error:** `Cannot update environment variable [OPENAI_API_KEY] to string literal`
**Solution:** The script automatically uses `--update-env-vars` as fallback

#### 3. GCP API Not Enabled
**Error:** `API [cloudbuild.googleapis.com] not enabled`
**Solution:** Run `./deploy/deploy-all.sh` which auto-enables APIs

#### 4. Authentication Issues
**Error:** `gcloud auth required`
**Solution:**
```bash
gcloud auth login
gcloud config set project YOUR_PROJECT_ID
```

### Debug Mode

Enable verbose logging:
```bash
set -x  # Add to script top for debug mode
./deploy/deploy-service.sh slackbot 2>&1 | tee debug.log
```

### Health Checks

Verify deployments:
```bash
# Check service health
curl https://slackbot-service-xxx.us-central1.run.app/health

# Check all services
for service in transcript slackbot linear notion; do
  echo "Testing $service..."
  curl -f "https://${service}-service-xxx.us-central1.run.app/health" || echo "❌ $service failed"
done
```

## 🔒 Security Best Practices

1. **Environment Variables**: Never commit `.env` files
2. **IAM Permissions**: Use minimal required permissions
3. **Service Accounts**: Create dedicated deployment service accounts
4. **Secret Management**: Consider using GCP Secret Manager for production

### Recommended IAM Roles
```bash
# For deployment service account
gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:deployment@$PROJECT_ID.iam.gserviceaccount.com" \
  --role="roles/cloudbuild.builds.editor"
  
gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:deployment@$PROJECT_ID.iam.gserviceaccount.com" \
  --role="roles/run.admin"
```

## 🎯 Production Deployment Checklist

- [ ] Environment variables configured
- [ ] GCP project and billing set up
- [ ] Required APIs enabled
- [ ] Service account permissions configured
- [ ] Health check endpoints implemented
- [ ] Monitoring and alerting configured
- [ ] Backup and rollback strategy defined

## 🐛 Reporting Issues

For deployment issues:
1. Check individual service logs: `deploy-<service>.log`
2. Verify environment variables: `cat .env`
3. Test GCP connectivity: `gcloud auth list`
4. Check service health: `curl <service-url>/health`

## 📚 Additional Resources

- [Google Cloud Run Documentation](https://cloud.google.com/run/docs)
- [Cloud Build Documentation](https://cloud.google.com/build/docs)
- [Alpha Machine Architecture](../docs/architecture.md) 