import json
import time
import os
import subprocess
import ast
from dotenv import load_dotenv
from typing import Dict, Any, List

# Load environment variables from .env file
load_dotenv()

from quantum_translator_agent import TranslatorAgent
from circuit_architect_agent import ArchitectAgent
from quantum_scientist_agent import ScientistAgent
from evaluator_agent import EvaluatorAgent
from media_generator_agent import MediaProducerAgent
from session_manager import SessionManager

# Stage ordering used to determine which steps to skip on resume
STAGE_ORDER = ["CREATED", "TRANSLATED", "ARCHITECTED", "AUDITED", "EVALUATED", "COMPLETED"]


class QuantumOrchestrator:
    def __init__(self):
        self.translator = TranslatorAgent()
        self.architect = ArchitectAgent()
        self.scientist = ScientistAgent()
        self.evaluator = EvaluatorAgent()
        self.media_producer = MediaProducerAgent()
        self.max_retries = 3
        self.session_manager = SessionManager()

    def _past_stage(self, current_stage: str, target_stage: str) -> bool:
        """Return True if current_stage is at or past target_stage."""
        return STAGE_ORDER.index(current_stage) >= STAGE_ORDER.index(target_stage)

    async def run_workflow(self, user_input: str, event_callback, session_id: str = None) -> Dict[str, Any]:
        # --- SESSION SETUP ---
        resuming = False
        session_data = {}
        resume_stage = "CREATED"

        if session_id:
            loaded = self.session_manager.load_session(session_id)
            if loaded:
                resuming = True
                session_data = loaded["data"]
                resume_stage = loaded["stage"]
                user_input = loaded["user_input"]
                await event_callback({
                    "type": "progress", "agent": "Orchestrator",
                    "status": f"Resuming session from stage: {resume_stage}",
                    "session_id": session_id,
                })
            else:
                await event_callback({
                    "type": "warning", "agent": "Orchestrator",
                    "status": "Session not found. Starting fresh.",
                })
                session_id = None

        if not session_id:
            session_id = self.session_manager.create_session(user_input)

        await event_callback({
            "type": "progress", "agent": "Orchestrator",
            "status": f"Starting Quantum Workflow for: '{user_input}'",
            "session_id": session_id,
        })

        # --- STEP 1: TRANSLATION ---
        if resuming and self._past_stage(resume_stage, "TRANSLATED"):
            mapping = session_data["mapping"]
            algo = mapping.get('identified_algorithm', mapping.get('algorithm', 'Unknown'))
            await event_callback({"type": "success", "agent": "Translator", "status": f"[Restored] Problem mapped to: {algo}", "restored": True})
        else:
            await event_callback({"type": "progress", "agent": "Translator", "status": "Translating natural language to quantum problem mapping..."})
            time.sleep(2)
            mapping = self.translator.map_problem(user_input)

            if 'error' in mapping:
                await event_callback({"type": "error", "agent": "Translator", "status": "Translation failed", "details": mapping})
                return {"error": "Translation failed", "details": mapping}

            algo = mapping.get('identified_algorithm', mapping.get('algorithm', 'Unknown'))
            await event_callback({"type": "success", "agent": "Translator", "status": f"Problem mapped to: {algo}"})
            self.session_manager.checkpoint(session_id, "TRANSLATED", {"mapping": mapping})

        # --- STEP 2-4: ARCHITECTURE & VALIDATION LOOP ---
        attempt = session_data.get("attempt", 0) if resuming else 0
        validated_code = None
        scientific_report = session_data.get("scientific_report") if resuming else None
        evaluator_report = None
        nisq_warning = session_data.get("nisq_warning") if resuming else None

        # Determine where to resume inside the loop
        skip_architect = resuming and self._past_stage(resume_stage, "ARCHITECTED")
        skip_scientist = resuming and self._past_stage(resume_stage, "AUDITED")
        skip_evaluator = resuming and self._past_stage(resume_stage, "EVALUATED")

        # If fully evaluated, skip the entire loop
        if skip_evaluator:
            validated_code = {"python_code": session_data.get("code_package", {}).get("python_code", ""),
                              **session_data.get("code_package", {})}
            await event_callback({"type": "success", "agent": "Evaluator", "status": "[Restored] Evaluator Validation Passed.", "restored": True})
        else:
            while attempt < self.max_retries:
                attempt += 1

                # --- ARCHITECT ---
                if skip_architect and attempt == (session_data.get("attempt", 0) or 1):
                    code_package = session_data["code_package"]
                    python_code = code_package.get('python_code', code_package.get('code', ''))
                    await event_callback({"type": "success", "agent": "Architect", "status": "[Restored] Circuit generated successfully.", "restored": True})
                else:
                    skip_architect = False  # Only skip on the first iteration
                    skip_scientist = False
                    await event_callback({"type": "progress", "agent": "Architect", "status": f"Architecture Generation (Attempt {attempt})..."})
                    time.sleep(5)
                    code_package = self.architect.generate_code(mapping, feedback=scientific_report)
                    if 'error' in code_package:
                        await event_callback({"type": "error", "agent": "Architect", "status": f"Architect error: {code_package['error']}"})
                        continue

                    python_code = code_package.get('python_code', code_package.get('code', ''))
                    await event_callback({"type": "success", "agent": "Architect", "status": "Circuit generated successfully."})
                    self.session_manager.checkpoint(session_id, "ARCHITECTED", {
                        "code_package": code_package,
                    }, attempt=attempt)

                # --- SCIENTIST ---
                if skip_scientist and attempt == (session_data.get("attempt", 0) or 1):
                    scientific_report = session_data["scientific_report"]
                    decision = scientific_report.get('decision', 'REJECTED')
                    if decision in ("APPROVED", "WARNING"):
                        if decision == "WARNING":
                            nisq_warning = scientific_report.get('architect_feedback', '')
                            await event_callback({"type": "warning", "agent": "Scientist", "status": f"[Restored] ⚠ NISQ Warning: {nisq_warning}", "restored": True})
                        else:
                            await event_callback({"type": "success", "agent": "Scientist", "status": "[Restored] Scientific validation passed.", "restored": True})
                    else:
                        await event_callback({"type": "error", "agent": "Scientist", "status": f"[Restored] Rejected.", "restored": True})
                        continue
                else:
                    skip_scientist = False
                    await event_callback({"type": "progress", "agent": "Scientist", "status": "Auditing proposed quantum circuit..."})
                    time.sleep(5)
                    scientific_report = self.scientist.validate_proposal(mapping, python_code)

                    decision = scientific_report.get('decision', 'REJECTED')

                    if decision in ("APPROVED", "WARNING"):
                        if decision == "WARNING":
                            nisq_warning = scientific_report.get('architect_feedback', 'Circuit may exceed NISQ hardware coherence limits.')
                            await event_callback({"type": "warning", "agent": "Scientist", "status": f"⚠ NISQ Warning (non-blocking): {nisq_warning}"})
                        else:
                            await event_callback({"type": "success", "agent": "Scientist", "status": "Scientific validation passed."})

                        self.session_manager.checkpoint(session_id, "AUDITED", {
                            "scientific_report": scientific_report,
                            "nisq_warning": nisq_warning,
                        }, attempt=attempt)
                    else:
                        feedback = scientific_report.get('architect_feedback', scientific_report.get('feedback', 'No detailed feedback'))
                        await event_callback({"type": "error", "agent": "Scientist", "status": f"Rejected. Reason: {feedback}"})
                        continue

                # --- EVALUATOR ---
                await event_callback({"type": "progress", "agent": "Evaluator", "status": "Running local simulation & final evaluation..."})
                time.sleep(5)

                actual_results = {"status": "FAILED", "histogram": {}}

                try:
                    with open("temp_circuit.py", "w", encoding="utf-8") as f:
                        f.write(python_code)

                    import sys
                    python_exe = sys.executable
                    result = subprocess.run([python_exe, "temp_circuit.py"], capture_output=True, text=True, timeout=60, encoding="utf-8")

                    if result.returncode == 0:
                        actual_results["status"] = "COMPLETED"
                        output = result.stdout.strip()
                        try:
                            dict_str_start = output.rfind('{')
                            dict_str_end = output.rfind('}')
                            if dict_str_start != -1 and dict_str_end != -1 and dict_str_end > dict_str_start:
                                dict_str = output[dict_str_start:dict_str_end+1]
                                parsed = ast.literal_eval(dict_str)
                                if isinstance(parsed, dict):
                                    actual_results["histogram"] = parsed
                                else:
                                    actual_results["raw_output"] = output
                            else:
                                actual_results["raw_output"] = output
                        except Exception:
                            actual_results["raw_output"] = output
                    else:
                        actual_results["error"] = result.stderr.strip().split('\n')[-3:]
                        await event_callback({"type": "warning", "agent": "Environment", "status": f"Sim execution failed: {actual_results['error']}"})
                except Exception as e:
                    actual_results["error"] = str(e)
                    await event_callback({"type": "warning", "agent": "Environment", "status": f"Code run hit error: {e}"})
                finally:
                    if os.path.exists("temp_circuit.py"):
                        os.remove("temp_circuit.py")

                evaluator_report = self.evaluator.evaluate_simulation(python_code, actual_results)

                verdict = evaluator_report.get('verdict', 'FAIL')
                if verdict == 'PASS':
                    validated_code = code_package
                    await event_callback({"type": "success", "agent": "Evaluator", "status": "Evaluator Validation Passed."})
                    self.session_manager.checkpoint(session_id, "EVALUATED", {
                        "evaluator_report": evaluator_report,
                        "code_package": code_package,
                    }, attempt=attempt)
                    break
                else:
                    reason = evaluator_report.get('validation_summary', '')
                    await event_callback({"type": "error", "agent": "Evaluator", "status": f"Rejected. Reason: {reason}"})
                    fix_instructions = evaluator_report.get('feedback_for_agents', 'Syntax or logic error detected. Review and fix the circuit.')
                    scientific_report = {"decision": "REJECTED", "architect_feedback": fix_instructions}

        if not validated_code:
            await event_callback({"type": "error", "agent": "Orchestrator", "status": "Could not generate a scientifically valid circuit after 3 attempts."})
            return {"error": "Could not generate a scientifically valid circuit after 3 attempts."}

        # --- STEP 5: MEDIA PRODUCTION ---
        await event_callback({"type": "progress", "agent": "MediaProducer", "status": "Generating multi-modal narrative and visual briefs..."})
        time.sleep(5)
        visual_brief = self.media_producer.generate_visuals(mapping, validated_code.get('python_code', validated_code.get('code', '')))

        await event_callback({"type": "success", "agent": "MediaProducer", "status": "Cinematic visual assets generated."})

        # FINAL OUTPUT ASSEMBLY
        final_package = {
            "metadata": {
                "algorithm": mapping.get('identified_algorithm', mapping.get('algorithm', 'Unknown')),
                "qubits": mapping.get('qubit_requirement_estimate', mapping.get('qubits', 0))
            },
            "code": validated_code.get('python_code', validated_code.get('code', '')),
            "explanation": validated_code.get('explanation', ''),
            "visuals": {
                "video_prompt": visual_brief.get('veo_video_prompt', visual_brief.get('video_prompt', '')),
                "image_prompt": visual_brief.get('imagen_graphic_prompt', visual_brief.get('image_prompt', ''))
            },
            "audio_narration": visual_brief.get('audio_script', ''),
            "nisq_warning": nisq_warning
        }

        # Mark session as COMPLETED and clean up
        self.session_manager.checkpoint(session_id, "COMPLETED", {})
        self.session_manager.delete_session(session_id)

        await event_callback({"type": "complete", "agent": "Orchestrator", "status": "Final Multimodal Package Ready!", "data": final_package})
        return final_package

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
import asyncio

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

session_manager = SessionManager()


@app.get("/")
def read_root():
    return {"message": "Quantum Orchestrator API is Live"}


@app.get("/sessions")
def list_sessions():
    """Return all resumable sessions."""
    return session_manager.list_sessions()


@app.delete("/sessions/{session_id}")
def delete_session(session_id: str):
    """Delete a saved session."""
    deleted = session_manager.delete_session(session_id)
    if deleted:
        return {"status": "deleted"}
    return {"status": "not_found"}


@app.websocket("/ws/simulate")
async def websocket_simulate(websocket: WebSocket):
    await websocket.accept()
    orchestrator = QuantumOrchestrator()
    try:
        raw = await websocket.receive_text()

        # Support both plain-text prompts and JSON payloads with optional session_id
        prompt = raw
        session_id = None
        try:
            payload = json.loads(raw)
            if isinstance(payload, dict):
                prompt = payload.get("prompt", raw)
                session_id = payload.get("session_id", None)
        except (json.JSONDecodeError, TypeError):
            pass  # treat as plain text prompt

        async def send_event_to_ws(event: dict):
            await websocket.send_json(event)
            await asyncio.sleep(0.1)

        result = await orchestrator.run_workflow(prompt, send_event_to_ws, session_id=session_id)

    except WebSocketDisconnect:
        print("Client disconnected.")
    except Exception as e:
        print(f"Error during simulation: {e}")
        await websocket.send_json({"type": "fatal", "agent": "Server", "status": str(e)})

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)