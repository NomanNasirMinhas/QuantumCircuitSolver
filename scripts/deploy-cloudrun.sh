#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

PROJECT_ID="${PROJECT_ID:-$(gcloud config get-value project 2>/dev/null || true)}"
REGION="${REGION:-us-central1}"
AR_REPO="${AR_REPO:-agentiq}"
BACKEND_SERVICE="${BACKEND_SERVICE:-agentiq-orchestrator}"
FRONTEND_SERVICE="${FRONTEND_SERVICE:-agentiq-frontend}"
CORS_ALLOW_ORIGINS="${CORS_ALLOW_ORIGINS:-https://your-frontend-domain.example}"
GCP_LOCATION="${GCP_LOCATION:-global}"
ACCESS_CODE_MASTER_PASSWORD="${ACCESS_CODE_MASTER_PASSWORD:-change-this-master-password}"
ACCESS_CODE_RESET_ENDPOINT="${ACCESS_CODE_RESET_ENDPOINT:-/admin/internal/7f1acb4e2a9244be9fd8c6d5a73b1e54/access-codes/reset}"
ACCESS_CODE_LIST_ENDPOINT="${ACCESS_CODE_LIST_ENDPOINT:-/admin/internal/2bf87f2d15fd43e1b9c4d8f0a56c7a91/access-codes/valid}"
ACCESS_CODE_STATE_FILE="${ACCESS_CODE_STATE_FILE:-/tmp/access_codes_state.json}"
ACCESS_CODE_BOOTSTRAP_COUNT="${ACCESS_CODE_BOOTSTRAP_COUNT:-5}"
RUN_HISTORY_GCS_BUCKET="${RUN_HISTORY_GCS_BUCKET:-__DISABLED__}"
RUN_HISTORY_GCS_PREFIX="${RUN_HISTORY_GCS_PREFIX:-successful_runs}"

if [[ -z "${PROJECT_ID}" ]]; then
  echo "PROJECT_ID is empty. Set PROJECT_ID or run: gcloud config set project <PROJECT_ID>"
  exit 1
fi

BACKEND_IMAGE="${REGION}-docker.pkg.dev/${PROJECT_ID}/${AR_REPO}/backend:latest"
FRONTEND_IMAGE="${REGION}-docker.pkg.dev/${PROJECT_ID}/${AR_REPO}/frontend:latest"

echo "==> Using PROJECT_ID=${PROJECT_ID}, REGION=${REGION}"

echo "==> Enabling required Google Cloud services"
gcloud services enable \
  run.googleapis.com \
  cloudbuild.googleapis.com \
  artifactregistry.googleapis.com \
  aiplatform.googleapis.com \
  --project "${PROJECT_ID}"

echo "==> Ensuring Artifact Registry repo exists: ${AR_REPO}"
if ! gcloud artifacts repositories describe "${AR_REPO}" \
  --location "${REGION}" \
  --project "${PROJECT_ID}" >/dev/null 2>&1; then
  gcloud artifacts repositories create "${AR_REPO}" \
    --repository-format=docker \
    --location="${REGION}" \
    --project "${PROJECT_ID}"
fi

echo "==> Deploying backend service: ${BACKEND_SERVICE}"
gcloud builds submit \
  --config cloudbuild.yaml \
  --substitutions="_REGION=${REGION},_SERVICE_NAME=${BACKEND_SERVICE},_IMAGE=${BACKEND_IMAGE},_CORS_ORIGINS=${CORS_ALLOW_ORIGINS},_GCP_LOCATION=${GCP_LOCATION},_ACCESS_CODE_MASTER_PASSWORD=${ACCESS_CODE_MASTER_PASSWORD},_ACCESS_CODE_RESET_ENDPOINT=${ACCESS_CODE_RESET_ENDPOINT},_ACCESS_CODE_LIST_ENDPOINT=${ACCESS_CODE_LIST_ENDPOINT},_ACCESS_CODE_STATE_FILE=${ACCESS_CODE_STATE_FILE},_ACCESS_CODE_BOOTSTRAP_COUNT=${ACCESS_CODE_BOOTSTRAP_COUNT},_RUN_HISTORY_GCS_BUCKET=${RUN_HISTORY_GCS_BUCKET},_RUN_HISTORY_GCS_PREFIX=${RUN_HISTORY_GCS_PREFIX}" \
  --project "${PROJECT_ID}" \
  .

echo "==> Ensuring backend is publicly invokable"
gcloud run services add-iam-policy-binding "${BACKEND_SERVICE}" \
  --platform managed \
  --region "${REGION}" \
  --project "${PROJECT_ID}" \
  --member="allUsers" \
  --role="roles/run.invoker" \
  --quiet

BACKEND_URL="$(gcloud run services describe "${BACKEND_SERVICE}" --region "${REGION}" --project "${PROJECT_ID}" --format='value(status.url)')"
if [[ -z "${BACKEND_URL}" ]]; then
  echo "Failed to resolve backend URL after deploy."
  exit 1
fi

BACKEND_HOST="${BACKEND_URL#https://}"
WS_URL="wss://${BACKEND_HOST}/ws/simulate"

echo "==> Backend URL: ${BACKEND_URL}"
echo "==> Frontend will use API=${BACKEND_URL} and WS=${WS_URL}"

echo "==> Deploying frontend service: ${FRONTEND_SERVICE}"
gcloud builds submit \
  --config frontend/cloudbuild.yaml \
  --substitutions="_REGION=${REGION},_SERVICE_NAME=${FRONTEND_SERVICE},_IMAGE=${FRONTEND_IMAGE},_API_BASE_URL=${BACKEND_URL},_WS_URL=${WS_URL}" \
  --project "${PROJECT_ID}" \
  frontend

echo "==> Ensuring frontend is publicly invokable"
gcloud run services add-iam-policy-binding "${FRONTEND_SERVICE}" \
  --platform managed \
  --region "${REGION}" \
  --project "${PROJECT_ID}" \
  --member="allUsers" \
  --role="roles/run.invoker" \
  --quiet

FRONTEND_URL="$(gcloud run services describe "${FRONTEND_SERVICE}" --region "${REGION}" --project "${PROJECT_ID}" --format='value(status.url)')"

echo ""
echo "Deployment complete."
echo "Backend : ${BACKEND_URL}"
echo "Frontend: ${FRONTEND_URL}"
