#!/usr/bin/env bash
set -e

# ==============================================================================
# Google Cloud Platform (GCP) Automated Deployment Script
# Deploys Daily GenAI News Aggregator as a Cloud Run Job + Cloud Scheduler
# ==============================================================================

# Check if gcloud is installed
if ! command -v gcloud &> /dev/null; then
    echo "❌ Error: 'gcloud' CLI is not installed. Please install Google Cloud SDK."
    exit 1
fi

# Load variables or prompt
PROJECT_ID="${GCP_PROJECT_ID:-ai-alerts-509405}"
REGION="${GCP_REGION:-us-central1}"
JOB_NAME="genai-daily-briefing"
REPOSITORY_NAME="genai-briefing-repo"
SCHEDULER_NAME="genai-briefing-daily-trigger"
CRON_SCHEDULE="30 0 * * *" # 00:30 UTC = 06:00 AM IST
TIMEZONE="Asia/Kolkata"

if [ -z "$PROJECT_ID" ]; then
    echo "⚠️  No GCP Project ID set in gcloud config."
    read -p "Enter your GCP Project ID: " PROJECT_ID
    gcloud config set project "$PROJECT_ID"
fi

echo "======================================================================"
echo "🚀 Deploying Daily GenAI News Aggregator to GCP"
echo "Project ID : $PROJECT_ID"
echo "Region     : $REGION"
echo "Job Name   : $JOB_NAME"
echo "Schedule   : $CRON_SCHEDULE ($TIMEZONE)"
echo "======================================================================"

# 1. Enable required GCP APIs
echo "📌 [1/5] Enabling GCP Services (Artifact Registry, Cloud Run, Cloud Scheduler, Secret Manager)..."
gcloud services enable \
    artifactregistry.googleapis.com \
    run.googleapis.com \
    cloudscheduler.googleapis.com \
    secretmanager.googleapis.com

# 2. Create Artifact Registry Repository if not exists
echo "📌 [2/5] Setting up Artifact Registry..."
if ! gcloud artifacts repositories describe "$REPOSITORY_NAME" --location="$REGION" &>/dev/null; then
    gcloud artifacts repositories create "$REPOSITORY_NAME" \
        --repository-format=docker \
        --location="$REGION" \
        --description="Docker repository for GenAI Daily Briefing"
fi

IMAGE_TAG="$REGION-docker.pkg.dev/$PROJECT_ID/$REPOSITORY_NAME/$JOB_NAME:latest"

# 3. Build and Push Container Image
echo "📌 [3/5] Building and pushing Docker container image via Google Cloud Build..."
gcloud builds submit --tag "$IMAGE_TAG" .

# 4. Create or Update Cloud Run Job
echo "📌 [4/5] Deploying Cloud Run Job..."
# Load secrets or env vars from local .env if present
ENV_FILE_FLAGS=""
if [ -f .env ]; then
    echo "   Using environment variables from local .env file..."
    ENV_FILE_FLAGS="--env-vars-file=.env"
fi

gcloud run jobs deploy "$JOB_NAME" \
    --image="$IMAGE_TAG" \
    --region="$REGION" \
    --tasks=1 \
    --max-retries=1 \
    --task-timeout=10m \
    --cpu=1 \
    --memory=512Mi \
    $ENV_FILE_FLAGS

# 5. Create or Update Cloud Scheduler Trigger
echo "📌 [5/5] Setting up Cloud Scheduler (06:00 AM IST)..."
SERVICE_ACCOUNT_NAME="cloud-run-job-invoker"
SERVICE_ACCOUNT_EMAIL="$SERVICE_ACCOUNT_NAME@$PROJECT_ID.iam.gserviceaccount.com"

# Create service account if not exists
if ! gcloud iam service-accounts describe "$SERVICE_ACCOUNT_EMAIL" &>/dev/null; then
    gcloud iam service-accounts create "$SERVICE_ACCOUNT_NAME" \
        --display-name="Cloud Run Job Invoker Service Account"
fi

# Grant Cloud Run Developer permission to service account
gcloud projects add-iam-policy-binding "$PROJECT_ID" \
    --member="serviceAccount:$SERVICE_ACCOUNT_EMAIL" \
    --role="roles/run.developer" &>/dev/null

if gcloud scheduler jobs describe "$SCHEDULER_NAME" --location="$REGION" &>/dev/null; then
    gcloud scheduler jobs update execution "$SCHEDULER_NAME" \
        --location="$REGION" \
        --schedule="$CRON_SCHEDULE" \
        --time-zone="$TIMEZONE" \
        --uri="https://$REGION-run.googleapis.com/apis/run.googleapis.com/v1/namespaces/$PROJECT_ID/jobs/$JOB_NAME:run" \
        --http-method=POST \
        --oauth-service-account-email="$SERVICE_ACCOUNT_EMAIL"
else
    gcloud scheduler jobs create execution "$SCHEDULER_NAME" \
        --location="$REGION" \
        --schedule="$CRON_SCHEDULE" \
        --time-zone="$TIMEZONE" \
        --uri="https://$REGION-run.googleapis.com/apis/run.googleapis.com/v1/namespaces/$PROJECT_ID/jobs/$JOB_NAME:run" \
        --http-method=POST \
        --oauth-service-account-email="$SERVICE_ACCOUNT_EMAIL"
fi

echo "======================================================================"
echo "✅ DEPLOYMENT SUCCESSFUL!"
echo "Cloud Run Job deployed: $JOB_NAME ($REGION)"
echo "Cloud Scheduler active: $SCHEDULER_NAME (Daily at 06:00 AM IST)"
echo ""
echo "To test execution immediately in GCP, run:"
echo "  gcloud run jobs execute $JOB_NAME --region=$REGION"
echo "======================================================================"
