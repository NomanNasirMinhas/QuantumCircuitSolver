#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

PROJECT_ID="${PROJECT_ID:-$(gcloud config get-value project 2>/dev/null || true)}"
REGION="${REGION:-us-central1}"
AR_REPO="${AR_REPO:-quantum-circuit-solver}"
BACKEND_SERVICE="${BACKEND_SERVICE:-quantum-circuit-orchestrator}"
FRONTEND_SERVICE="${FRONTEND_SERVICE:-quantum-circuit-frontend}"
CORS_ALLOW_ORIGINS="${CORS_ALLOW_ORIGINS:-https://your-frontend-domain.example}"
GCP_LOCATION="${GCP_LOCATION:-global}"

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
  --substitutions="_REGION=${REGION},_SERVICE_NAME=${BACKEND_SERVICE},_IMAGE=${BACKEND_IMAGE},_CORS_ORIGINS=${CORS_ALLOW_ORIGINS},_GCP_LOCATION=${GCP_LOCATION}" \
  --project "${PROJECT_ID}" \
  .

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

FRONTEND_URL="$(gcloud run services describe "${FRONTEND_SERVICE}" --region "${REGION}" --project "${PROJECT_ID}" --format='value(status.url)')"

echo ""
echo "Deployment complete."
echo "Backend : ${BACKEND_URL}"
echo "Frontend: ${FRONTEND_URL}"
