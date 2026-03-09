# AgentiQ
A Multi-Agent Quantum Engineering Platform With Storyline Delivery

## Project Overview
**AgentiQ** is an end-to-end AI pipeline that translates real-world problems into verified quantum circuits, simulates them, and presents the result as a guided storyline book. A swarm of specialized Google Generative AI agents collaborates sequentially to map the problem, generate Qiskit code, validate scientific correctness, execute simulation, and produce page-based explanatory media with per-page narration.

## Architecture And Agent Roles
The backend drives a cyclic, self-correcting workflow utilizing 5 distinct AI personas:

1. **Translator Agent (Logic Mapper)**
   - **Role:** Understands the user's natural language problem and classifies it into a quantum problem space (e.g., Unstructured Search, Combinatorial Optimization).
   - **Output:** Identifies the target quantum algorithm (e.g., Grover's, QAOA) and provides a pedagogical "Quantum Story Context" explaining the approach.

2. **Circuit Architect Agent (Qiskit Engineer)**
   - **Role:** Takes the logical mapping and writes production-ready Qiskit 1.x Python code.
   - **Output:** Generates the actual quantum circuit code, enforcing constraints like NISQ (Noisy Intermediate-Scale Quantum) scaling to maintain a realistic, compilable circuit payload.

3. **Scientist Agent (Technical Auditor)**
   - **Role:** Acts as the strict scientific quality gate. It verifies that the generated code aligns with physical quantum mechanics laws (e.g., No-Cloning Theorem, Reversibility) and realistic hardware coherence limits.
   - **Behavior:** It checks the circuit depth and can provide detailed mathematical feedback to force the Architect to rewrite invalid circuits.

4. **Evaluator Agent (Simulation Gatekeeper)**
   - **Role:** Executes the generated Qiskit circuit payload on a local machine (using `AerSimulator`).
   - **Output:** Analyzes the simulator's standard output (histograms/shot counts) to ensure the circuit compiles, runs without syntax errors, and solves the core logic. Generates a Pass/Fail verdict.

5. **Media Producer Agent (Storyline Creator)**
   - **Role:** Converts the technical quantum result into a coherent page-by-page learning experience.
   - **Output:** Produces a combined storybook where each page includes page text, a generated illustration, and dedicated narration audio.

## Storyline Flow
1. User submits a problem prompt.
2. Agents derive and validate an executable quantum circuit.
3. Media producer generates a multi-page storyline plan tied to the exact algorithm and code.
4. Each page is rendered with:
   - Page text
   - Page illustration (Imagen)
   - Page narration audio (Gemini TTS)
5. Frontend presents the result in a page-turn reader with per-page "Listen" audio controls.

## Presentation Layer (Frontend)
The user interacts with the system via a visually stunning **Next.js & React Three Fiber** environment:
- **3D Quantum Particle Field:** A dynamic, immersive background that reacts to the simulation state.
- **Real-Time Execution Graph:** A live, re-arrangeable `React Flow` node graph that maps every websocket event, visually plotting the back-and-forth interactions and attempts among the agents.
- **Storybook Delivery:** Once the pipeline completes, the UI renders the generated code, Qiskit `circuit_diagram`, simulation `result_diagram` (histogram), and the page-based storyline reader with per-page audio.

## ADK Migration Status
The backend agents are now implemented on **Google Agent Development Kit (ADK)**:

- `TranslatorAgent` -> ADK `LlmAgent`
- `ArchitectAgent` -> ADK `LlmAgent`
- `ScientistAgent` -> ADK `LlmAgent`
- `EvaluatorAgent` -> ADK `LlmAgent`
- `MediaProducerAgent` storyline page planner -> ADK `LlmAgent`

The orchestrator keeps the same method contracts and websocket protocol, but each agent call now runs through ADK `Runner` sessions.

## Run Locally
```bash
pip install -r requirements.txt
python orchestrator.py
```

## Storybook Configuration
- `STORYBOOK_PAGE_COUNT=8`: number of pages to generate (clamped to `2..16`).
- `MEDIA_STORYBOOK_MODEL`: optional Gemini model override for storyline page planning.
- `IMAGEN_MODEL`: optional Imagen model override for per-page illustrations.
- `GEMINI_TTS_MODEL`: optional Gemini TTS model override for per-page narration.

## Deploy AgentiQ To Google Cloud Run (Recommended)
This deploys your current `orchestrator.py` backend and the Next.js frontend.

### One-command deploy (Cloud Shell)
```bash
export PROJECT_ID="your-gcp-project-id"
export REGION="us-central1"
export AR_REPO="agentiq"
export BACKEND_SERVICE="agentiq-orchestrator"
export FRONTEND_SERVICE="agentiq-frontend"
export CORS_ALLOW_ORIGINS="https://your-frontend-domain.example"
export ACCESS_CODE_MASTER_PASSWORD="your-strong-master-password"
export ACCESS_CODE_RESET_ENDPOINT="/admin/access/reset"
export ACCESS_CODE_LIST_ENDPOINT="/admin/access/list"
export ACCESS_CODE_BOOTSTRAP_COUNT="5"
export RUN_HISTORY_GCS_BUCKET="your-persistent-history-bucket"
export RUN_HISTORY_GCS_PREFIX="successful_runs"
bash scripts/deploy-cloudrun.sh
```

### One-command deploy (PowerShell)
```powershell
$env:PROJECT_ID="your-gcp-project-id"
$env:REGION="us-central1"
$env:AR_REPO="agentiq"
$env:BACKEND_SERVICE="agentiq-orchestrator"
$env:FRONTEND_SERVICE="agentiq-frontend"
$env:CORS_ALLOW_ORIGINS="https://your-frontend-domain.example"
$env:ACCESS_CODE_MASTER_PASSWORD="your-strong-master-password"
$env:ACCESS_CODE_RESET_ENDPOINT="/admin/access/reset"
$env:ACCESS_CODE_LIST_ENDPOINT="/admin/access/list"
$env:ACCESS_CODE_BOOTSTRAP_COUNT="5"
$env:RUN_HISTORY_GCS_BUCKET="your-persistent-history-bucket"
$env:RUN_HISTORY_GCS_PREFIX="successful_runs"
.\scripts\deploy-cloudrun.ps1
```

### Access code gate behavior
- Backend generates one-time access codes at runtime on startup (`ACCESS_CODE_BOOTSTRAP_COUNT`, default `5`).
- Frontend requires a valid code before showing the main prompt/agent screen.
- On successful validation, code is consumed and cannot be reused.
- One consumed code grants exactly one prompt run.
- When all codes are used, frontend shows "all codes exhausted, ask admin to reset."

### Admin reset route
The backend exposes a configurable admin reset endpoint (set via required `ACCESS_CODE_RESET_ENDPOINT` env var).

Call it with the master password in the `Authorization` header:
```bash
curl -X POST "https://YOUR_BACKEND_URL/YOUR_RESET_ENDPOINT" \
  -H "Authorization: Bearer YOUR_MASTER_PASSWORD"
```

This returns a freshly generated set of access codes (`ACCESS_CODE_BOOTSTRAP_COUNT`, default `5`).

### Persist successful runs across deployments
To keep successful run history after Cloud Run instance restarts/deployments, set:
- `RUN_HISTORY_GCS_BUCKET=<your-gcs-bucket>`
- `RUN_HISTORY_GCS_PREFIX=successful_runs` (optional folder prefix)

The backend syncs each completed run folder to GCS and `/runs/history` merges local + GCS completed runs.

### Admin list valid codes route
The backend exposes another configurable endpoint to list currently valid (unused) codes (set via required `ACCESS_CODE_LIST_ENDPOINT` env var).

```bash
curl -X POST "https://YOUR_BACKEND_URL/YOUR_LIST_ENDPOINT" \
  -H "Authorization: Bearer YOUR_MASTER_PASSWORD"
```

### What the script does
1. Enables required APIs (`run`, `cloudbuild`, `artifactregistry`, `aiplatform`).
2. Ensures Artifact Registry repo exists.
3. Builds/deploys backend service from `cloudbuild.yaml`.
4. Resolves backend URL and computes websocket URL (`wss://.../ws/simulate`).
5. Builds/deploys frontend service from `frontend/cloudbuild.yaml` with correct runtime URLs.

## Reproducible Testing
Run the checks below in order. They validate that admin endpoint env vars are mandatory and that auth behavior is stable.

### 1) Missing admin endpoint env vars must fail
PowerShell:
```powershell
$env:ACCESS_CODE_RESET_ENDPOINT=""
$env:ACCESS_CODE_LIST_ENDPOINT=""
python orchestrator.py
```
Expected result: process exits immediately with `RuntimeError` mentioning the missing env var.

Bash:
```bash
unset ACCESS_CODE_RESET_ENDPOINT
unset ACCESS_CODE_LIST_ENDPOINT
python orchestrator.py
```
Expected result: process exits immediately with `RuntimeError` mentioning the missing env var.

### 2) Backend starts when required env vars are set
PowerShell:
```powershell
$env:ACCESS_CODE_MASTER_PASSWORD="your-strong-master-password"
$env:ACCESS_CODE_RESET_ENDPOINT="/admin/access/reset"
$env:ACCESS_CODE_LIST_ENDPOINT="/admin/access/list"
python orchestrator.py
```
Expected result: server starts successfully.

### 3) Admin endpoint auth behavior is deterministic
Without auth header (expect `401`):
```bash
curl -i -X POST "http://localhost:8000/admin/access/list"
```
With valid bearer token (expect `200`):
```bash
curl -i -X POST "http://localhost:8000/admin/access/list" \
  -H "Authorization: Bearer your-strong-master-password"
```

### 4) Build guard fails early when admin endpoint substitutions are missing
```bash
gcloud builds submit --config cloudbuild.yaml \
  --substitutions=_REGION=us-central1,_SERVICE_NAME=agentiq-orchestrator,_IMAGE=us-central1-docker.pkg.dev/$PROJECT_ID/agentiq/backend:latest,_CORS_ORIGINS=https://example.com,_GCP_LOCATION=global,_ACCESS_CODE_MASTER_PASSWORD=secret,_ACCESS_CODE_RESET_ENDPOINT=,_ACCESS_CODE_LIST_ENDPOINT=,_ACCESS_CODE_STATE_FILE=/tmp/access_codes_state.json,_ACCESS_CODE_BOOTSTRAP_COUNT=5,_RUN_HISTORY_GCS_BUCKET=__DISABLED__,_RUN_HISTORY_GCS_PREFIX=successful_runs
```
Expected result: Cloud Build fails in the first step with a message that `_ACCESS_CODE_RESET_ENDPOINT` or `_ACCESS_CODE_LIST_ENDPOINT` is required.

### Manual deploy (if needed)
Backend:
```bash
gcloud builds submit --config cloudbuild.yaml \
  --substitutions=_REGION=us-central1,_SERVICE_NAME=agentiq-orchestrator,_IMAGE=us-central1-docker.pkg.dev/$PROJECT_ID/agentiq/backend:latest,_CORS_ORIGINS=https://your-frontend-domain.example,_ACCESS_CODE_RESET_ENDPOINT=/admin/access/reset,_ACCESS_CODE_LIST_ENDPOINT=/admin/access/list
```

Frontend:
```bash
gcloud builds submit frontend --config frontend/cloudbuild.yaml \
  --substitutions=_REGION=us-central1,_SERVICE_NAME=agentiq-frontend,_IMAGE=us-central1-docker.pkg.dev/$PROJECT_ID/agentiq/frontend:latest,_API_BASE_URL=https://your-backend-url,_WS_URL=wss://your-backend-url/ws/simulate
```

## ADK App For Google Cloud
An ADK-native deployable app is included at:

- `adk_agents/quantum_orchestrator/agent.py` (path retained for compatibility)

Run ADK API server locally:
```bash
adk api_server adk_agents --host 0.0.0.0 --port 8000
```

Deploy to Cloud Run from Google Console/Cloud Shell:
```bash
adk deploy cloud_run --project YOUR_PROJECT --region YOUR_REGION adk_agents/quantum_orchestrator
```

```bash
gcloud artifacts repositories create agentiq --repository-format=docker --location=us-central1 --project=YOUR_PROJECT
```

```bash
gcloud artifacts repositories list --location=us-central1 --project=YOUR_PROJECT
```
