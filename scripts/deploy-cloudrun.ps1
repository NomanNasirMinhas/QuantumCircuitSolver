param(
  [string]$ProjectId = $env:PROJECT_ID,
  [string]$Region = $(if ($env:REGION) { $env:REGION } else { "us-central1" }),
  [string]$ArRepo = $(if ($env:AR_REPO) { $env:AR_REPO } else { "agentiq" }),
  [string]$BackendService = $(if ($env:BACKEND_SERVICE) { $env:BACKEND_SERVICE } else { "agentiq-orchestrator" }),
  [string]$FrontendService = $(if ($env:FRONTEND_SERVICE) { $env:FRONTEND_SERVICE } else { "agentiq-frontend" }),
  [string]$CorsAllowOrigins = $(if ($env:CORS_ALLOW_ORIGINS) { $env:CORS_ALLOW_ORIGINS } else { "https://your-frontend-domain.example" }),
  [string]$GcpLocation = $(if ($env:GCP_LOCATION) { $env:GCP_LOCATION } else { "global" }),
  [string]$AccessCodeMasterPassword = $(if ($env:ACCESS_CODE_MASTER_PASSWORD) { $env:ACCESS_CODE_MASTER_PASSWORD } else { "" }),
  [string]$AccessCodeResetEndpoint = $(if ($env:ACCESS_CODE_RESET_ENDPOINT) { $env:ACCESS_CODE_RESET_ENDPOINT } else { "" }),
  [string]$AccessCodeListEndpoint = $(if ($env:ACCESS_CODE_LIST_ENDPOINT) { $env:ACCESS_CODE_LIST_ENDPOINT } else { "" }),
  [string]$AccessCodeStateFile = $(if ($env:ACCESS_CODE_STATE_FILE) { $env:ACCESS_CODE_STATE_FILE } else { "/tmp/access_codes_state.json" }),
  [string]$AccessCodeBootstrapCount = $(if ($env:ACCESS_CODE_BOOTSTRAP_COUNT) { $env:ACCESS_CODE_BOOTSTRAP_COUNT } else { "5" }),
  [string]$RunHistoryGcsBucket = $(if ($env:RUN_HISTORY_GCS_BUCKET) { $env:RUN_HISTORY_GCS_BUCKET } else { "" }),
  [string]$RunHistoryGcsPrefix = $(if ($env:RUN_HISTORY_GCS_PREFIX) { $env:RUN_HISTORY_GCS_PREFIX } else { "successful_runs" })
)
#RUN_HISTORY_GCS_BUCKET=__DISABLED__ to disable run history uploads
$ErrorActionPreference = "Stop"
if ($PSVersionTable.PSVersion.Major -ge 7) {
  $PSNativeCommandUseErrorActionPreference = $true
}

if (-not $ProjectId) {
  $ProjectId = (gcloud config get-value project).Trim()
}
if (-not $ProjectId) {
  throw "PROJECT_ID is empty. Set PROJECT_ID or run: gcloud config set project <PROJECT_ID>"
}
if ([string]::IsNullOrWhiteSpace($RunHistoryGcsBucket)) {
  $RunHistoryGcsBucket = "$ProjectId-agentiq-run-history"
}

$rootDir = Split-Path -Parent $PSScriptRoot
Set-Location $rootDir

$backendImage = "$Region-docker.pkg.dev/$ProjectId/$ArRepo/backend:latest"
$frontendImage = "$Region-docker.pkg.dev/$ProjectId/$ArRepo/frontend:latest"

Write-Host "==> Using PROJECT_ID=$ProjectId, REGION=$Region"
Write-Host "==> Using RUN_HISTORY_GCS_BUCKET=$RunHistoryGcsBucket"

Write-Host "==> Enabling required Google Cloud services"
gcloud services enable `
  run.googleapis.com `
  cloudbuild.googleapis.com `
  artifactregistry.googleapis.com `
  storage.googleapis.com `
  aiplatform.googleapis.com `
  --project $ProjectId

Write-Host "==> Ensuring Artifact Registry repo exists: $ArRepo"
$repoExists = $false
try {
  $null = & gcloud artifacts repositories describe $ArRepo --location $Region --project $ProjectId --format "value(name)"
  if ($LASTEXITCODE -eq 0) {
    $repoExists = $true
  }
} catch {
  $repoExists = $false
}
if (-not $repoExists) {
  & gcloud artifacts repositories create $ArRepo `
    --repository-format=docker `
    --location $Region `
    --project $ProjectId
  if ($LASTEXITCODE -ne 0) {
    throw "Failed to create Artifact Registry repo '$ArRepo' in region '$Region'."
  }
}

if ($RunHistoryGcsBucket.ToLowerInvariant() -ne "__disabled__") {
  Write-Host "==> Ensuring GCS bucket exists: gs://$RunHistoryGcsBucket"
  $bucketExists = $false
  try {
    $null = & gcloud storage buckets describe "gs://$RunHistoryGcsBucket" --project $ProjectId --format "value(name)"
    if ($LASTEXITCODE -eq 0) {
      $bucketExists = $true
    }
  } catch {
    $bucketExists = $false
  }
  if (-not $bucketExists) {
    & gcloud storage buckets create "gs://$RunHistoryGcsBucket" `
      --location $Region `
      --uniform-bucket-level-access `
      --project $ProjectId
    if ($LASTEXITCODE -ne 0) {
      throw "Failed to create GCS bucket 'gs://$RunHistoryGcsBucket' in location '$Region'."
    }
  }
} else {
  Write-Host "==> RUN_HISTORY_GCS_BUCKET is disabled; skipping bucket creation"
}

Write-Host "==> Deploying backend service: $BackendService"
$backendSubs = "_REGION=$Region,_SERVICE_NAME=$BackendService,_IMAGE=$backendImage,_CORS_ORIGINS=$CorsAllowOrigins,_GCP_LOCATION=$GcpLocation,_ACCESS_CODE_MASTER_PASSWORD=$AccessCodeMasterPassword,_ACCESS_CODE_RESET_ENDPOINT=$AccessCodeResetEndpoint,_ACCESS_CODE_LIST_ENDPOINT=$AccessCodeListEndpoint,_ACCESS_CODE_STATE_FILE=$AccessCodeStateFile,_ACCESS_CODE_BOOTSTRAP_COUNT=$AccessCodeBootstrapCount,_RUN_HISTORY_GCS_BUCKET=$RunHistoryGcsBucket,_RUN_HISTORY_GCS_PREFIX=$RunHistoryGcsPrefix"
& gcloud builds submit `
  --config cloudbuild.yaml `
  --substitutions $backendSubs `
  --project $ProjectId `
  .
if ($LASTEXITCODE -ne 0) {
  throw "Backend Cloud Build failed. Fix the build error and rerun deploy."
}

Write-Host "==> Ensuring backend is publicly invokable"
& gcloud run services add-iam-policy-binding $BackendService `
  --region $Region `
  --project $ProjectId `
  --member "allUsers" `
  --role "roles/run.invoker" `
  --platform managed `
  --quiet
if ($LASTEXITCODE -ne 0) {
  throw "Failed to grant unauthenticated invoker on backend service '$BackendService'."
}

$backendUrl = (& gcloud run services describe $BackendService --region $Region --project $ProjectId --format "value(status.url)").Trim()
if ($LASTEXITCODE -ne 0) {
  throw "Backend service '$BackendService' not found after deploy."
}
if (-not $backendUrl) {
  throw "Failed to resolve backend URL after deploy."
}
$backendHost = $backendUrl -replace "^https://", ""
$wsUrl = "wss://$backendHost/ws/simulate"

Write-Host "==> Backend URL: $backendUrl"
Write-Host "==> Frontend will use API=$backendUrl and WS=$wsUrl"

Write-Host "==> Deploying frontend service: $FrontendService"
$frontendSubs = "_REGION=$Region,_SERVICE_NAME=$FrontendService,_IMAGE=$frontendImage,_API_BASE_URL=$backendUrl,_WS_URL=$wsUrl"
& gcloud builds submit frontend `
  --config frontend/cloudbuild.yaml `
  --substitutions $frontendSubs `
  --project $ProjectId
if ($LASTEXITCODE -ne 0) {
  throw "Frontend Cloud Build failed. Fix the build error and rerun deploy."
}

Write-Host "==> Ensuring frontend is publicly invokable"
& gcloud run services add-iam-policy-binding $FrontendService `
  --region $Region `
  --project $ProjectId `
  --member "allUsers" `
  --role "roles/run.invoker" `
  --platform managed `
  --quiet
if ($LASTEXITCODE -ne 0) {
  throw "Failed to grant unauthenticated invoker on frontend service '$FrontendService'."
}

$frontendUrl = (& gcloud run services describe $FrontendService --region $Region --project $ProjectId --format "value(status.url)").Trim()
if ($LASTEXITCODE -ne 0) {
  throw "Frontend service '$FrontendService' not found after deploy."
}

Write-Host ""
Write-Host "Deployment complete."
Write-Host "Backend : $backendUrl"
Write-Host "Frontend: $frontendUrl"
