param(
  [string]$ProjectId = $env:PROJECT_ID,
  [string]$Region = $(if ($env:REGION) { $env:REGION } else { "us-central1" }),
  [string]$ArRepo = $(if ($env:AR_REPO) { $env:AR_REPO } else { "quantum-circuit-solver" }),
  [string]$BackendService = $(if ($env:BACKEND_SERVICE) { $env:BACKEND_SERVICE } else { "quantum-circuit-orchestrator" }),
  [string]$FrontendService = $(if ($env:FRONTEND_SERVICE) { $env:FRONTEND_SERVICE } else { "quantum-circuit-frontend" }),
  [string]$CorsAllowOrigins = $(if ($env:CORS_ALLOW_ORIGINS) { $env:CORS_ALLOW_ORIGINS } else { "https://your-frontend-domain.example" }),
  [string]$GcpLocation = $(if ($env:GCP_LOCATION) { $env:GCP_LOCATION } else { "global" }),
  [string]$AccessCodeMasterPassword = $(if ($env:ACCESS_CODE_MASTER_PASSWORD) { $env:ACCESS_CODE_MASTER_PASSWORD } else { "change-this-master-password" }),
  [string]$AccessCodeResetEndpoint = $(if ($env:ACCESS_CODE_RESET_ENDPOINT) { $env:ACCESS_CODE_RESET_ENDPOINT } else { "/admin/internal/7f1acb4e2a9244be9fd8c6d5a73b1e54/access-codes/reset" }),
  [string]$AccessCodeListEndpoint = $(if ($env:ACCESS_CODE_LIST_ENDPOINT) { $env:ACCESS_CODE_LIST_ENDPOINT } else { "/admin/internal/2bf87f2d15fd43e1b9c4d8f0a56c7a91/access-codes/valid" }),
  [string]$AccessCodeStateFile = $(if ($env:ACCESS_CODE_STATE_FILE) { $env:ACCESS_CODE_STATE_FILE } else { "/tmp/access_codes_state.json" })
)

$ErrorActionPreference = "Stop"

if (-not $ProjectId) {
  $ProjectId = (gcloud config get-value project).Trim()
}
if (-not $ProjectId) {
  throw "PROJECT_ID is empty. Set PROJECT_ID or run: gcloud config set project <PROJECT_ID>"
}

$rootDir = Split-Path -Parent $PSScriptRoot
Set-Location $rootDir

$backendImage = "$Region-docker.pkg.dev/$ProjectId/$ArRepo/backend:latest"
$frontendImage = "$Region-docker.pkg.dev/$ProjectId/$ArRepo/frontend:latest"

Write-Host "==> Using PROJECT_ID=$ProjectId, REGION=$Region"

Write-Host "==> Enabling required Google Cloud services"
gcloud services enable `
  run.googleapis.com `
  cloudbuild.googleapis.com `
  artifactregistry.googleapis.com `
  aiplatform.googleapis.com `
  --project $ProjectId

Write-Host "==> Ensuring Artifact Registry repo exists: $ArRepo"
$repoExists = $true
try {
  gcloud artifacts repositories describe $ArRepo --location $Region --project $ProjectId *> $null
} catch {
  $repoExists = $false
}
if (-not $repoExists) {
  gcloud artifacts repositories create $ArRepo `
    --repository-format=docker `
    --location $Region `
    --project $ProjectId
}

Write-Host "==> Deploying backend service: $BackendService"
$backendSubs = "_REGION=$Region,_SERVICE_NAME=$BackendService,_IMAGE=$backendImage,_CORS_ORIGINS=$CorsAllowOrigins,_GCP_LOCATION=$GcpLocation,_ACCESS_CODE_MASTER_PASSWORD=$AccessCodeMasterPassword,_ACCESS_CODE_RESET_ENDPOINT=$AccessCodeResetEndpoint,_ACCESS_CODE_LIST_ENDPOINT=$AccessCodeListEndpoint,_ACCESS_CODE_STATE_FILE=$AccessCodeStateFile"
gcloud builds submit `
  --config cloudbuild.yaml `
  --substitutions $backendSubs `
  --project $ProjectId `
  .

$backendUrl = (gcloud run services describe $BackendService --region $Region --project $ProjectId --format "value(status.url)").Trim()
if (-not $backendUrl) {
  throw "Failed to resolve backend URL after deploy."
}
$backendHost = $backendUrl -replace "^https://", ""
$wsUrl = "wss://$backendHost/ws/simulate"

Write-Host "==> Backend URL: $backendUrl"
Write-Host "==> Frontend will use API=$backendUrl and WS=$wsUrl"

Write-Host "==> Deploying frontend service: $FrontendService"
$frontendSubs = "_REGION=$Region,_SERVICE_NAME=$FrontendService,_IMAGE=$frontendImage,_API_BASE_URL=$backendUrl,_WS_URL=$wsUrl"
gcloud builds submit frontend `
  --config frontend/cloudbuild.yaml `
  --substitutions $frontendSubs `
  --project $ProjectId

$frontendUrl = (gcloud run services describe $FrontendService --region $Region --project $ProjectId --format "value(status.url)").Trim()

Write-Host ""
Write-Host "Deployment complete."
Write-Host "Backend : $backendUrl"
Write-Host "Frontend: $frontendUrl"
