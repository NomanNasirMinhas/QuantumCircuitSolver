import json
import os
import subprocess
import ast
import base64
import asyncio
import tempfile
from typing import Dict, Any, List

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

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
MAX_PROMPT_LENGTH = int(os.getenv("MAX_PROMPT_LENGTH", "2000"))
MAX_ACTIVE_WORKFLOWS_PER_IP = int(os.getenv("MAX_ACTIVE_WORKFLOWS_PER_IP", "1"))
DEBUG_RUNS_DIR = os.getenv(
    "DEBUG_RUNS_DIR",
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "debug_runs"),
)


def _parse_allowed_origins() -> List[str]:
    raw = os.getenv("CORS_ALLOW_ORIGINS", "*").strip()
    if not raw:
        return ["*"]
    return [origin.strip() for origin in raw.split(",") if origin.strip()]


def _ensure_run_dir(session_id: str) -> str:
    path = os.path.join(DEBUG_RUNS_DIR, session_id)
    os.makedirs(path, exist_ok=True)
    return path


def _save_json(path: str, payload: Any) -> None:
    with open(path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)


def _save_text(path: str, content: str) -> None:
    with open(path, "w", encoding="utf-8") as f:
        f.write(content or "")


def _ext_from_mime(mime_type: str) -> str:
    mime = (mime_type or "").lower().strip()
    if "png" in mime:
        return ".png"
    if "jpeg" in mime or "jpg" in mime:
        return ".jpg"
    if "webp" in mime:
        return ".webp"
    if "mp4" in mime:
        return ".mp4"
    if "mpeg" in mime or "mp3" in mime:
        return ".mp3"
    if "wav" in mime or "l16" in mime or "pcm" in mime:
        return ".wav"
    return ".bin"


def _save_base64_file(path: str, b64_data: str) -> None:
    if not b64_data:
        return
    with open(path, "wb") as f:
        f.write(base64.b64decode(b64_data))


def _extract_histogram_from_stdout(output: str) -> Dict[str, Any]:
    dict_str_start = output.rfind("{")
    dict_str_end = output.rfind("}")
    if dict_str_start == -1 or dict_str_end == -1 or dict_str_end <= dict_str_start:
        return {}

    dict_str = output[dict_str_start:dict_str_end + 1]
    try:
        parsed = ast.literal_eval(dict_str)
        if isinstance(parsed, dict):
            return parsed
    except Exception:
        return {}
    return {}


def _simulate_python_code(python_code: str, timeout_sec: int = 60) -> Dict[str, Any]:
    actual_results: Dict[str, Any] = {"status": "FAILED", "histogram": {}}
    with tempfile.TemporaryDirectory(prefix="qcs_eval_") as workdir:
        script_path = os.path.join(workdir, "temp_circuit.py")
        with open(script_path, "w", encoding="utf-8") as f:
            f.write(python_code)

        import sys

        result = subprocess.run(
            [sys.executable, script_path],
            capture_output=True,
            text=True,
            timeout=timeout_sec,
            encoding="utf-8",
            cwd=workdir,
        )

        if result.returncode == 0:
            actual_results["status"] = "COMPLETED"
            output = (result.stdout or "").strip()
            histogram = _extract_histogram_from_stdout(output)
            if histogram:
                actual_results["histogram"] = histogram
            else:
                actual_results["raw_output"] = output
        else:
            stderr = (result.stderr or "").strip().split("\n")
            actual_results["error"] = stderr[-3:]

    return actual_results


def _generate_histogram_diagram_b64(histogram: Dict[str, Any]) -> str:
    if not histogram:
        return ""

    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    with tempfile.TemporaryDirectory(prefix="qcs_hist_") as workdir:
        out_path = os.path.join(workdir, "result_diagram.png")
        plt.figure(figsize=(8, 5))
        plt.bar(histogram.keys(), histogram.values(), color="#00E5FF")
        plt.title("Simulation Results Histogram")
        plt.xlabel("States")
        plt.ylabel("Counts / Probabilities")
        plt.xticks(rotation=45)
        plt.tight_layout()
        plt.savefig(out_path)
        plt.close()

        with open(out_path, "rb") as f:
            return base64.b64encode(f.read()).decode("utf-8")


def _render_circuit_diagram_b64(python_code: str, timeout_sec: int = 60) -> str:
    with tempfile.TemporaryDirectory(prefix="qcs_draw_") as workdir:
        script_path = os.path.join(workdir, "temp_circuit_draw.py")
        with open(script_path, "w", encoding="utf-8") as f:
            f.write(python_code)

        import sys

        subprocess.run(
            [sys.executable, script_path],
            capture_output=True,
            timeout=timeout_sec,
            cwd=workdir,
        )

        circuit_path = os.path.join(workdir, "circuit.png")
        if not os.path.exists(circuit_path):
            return ""

        with open(circuit_path, "rb") as f:
            return base64.b64encode(f.read()).decode("utf-8")


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

    async def _emit_content_chunk(
        self,
        event_callback,
        agent: str,
        content_type: str,
        content: str,
        mime_type: str = "",
        label: str = "",
    ) -> None:
        if not content:
            return
        event: Dict[str, Any] = {
            "type": "content_chunk",
            "agent": agent,
            "status": label or f"{content_type} chunk ready",
            "content_type": content_type,
            "content": content,
        }
        if mime_type:
            event["mime_type"] = mime_type
        if label:
            event["label"] = label
        await event_callback(event)

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

        run_dir = _ensure_run_dir(session_id)
        _save_text(os.path.join(run_dir, "input_prompt.txt"), user_input)
        _save_json(
            os.path.join(run_dir, "run_context.json"),
            {"session_id": session_id, "resuming": resuming, "resume_stage": resume_stage},
        )

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
            await asyncio.sleep(1)
            mapping = await asyncio.to_thread(self.translator.map_problem, user_input)

            if 'error' in mapping:
                await event_callback({"type": "error", "agent": "Translator", "status": "Translation failed", "details": mapping})
                return {"error": "Translation failed", "details": mapping}

            algo = mapping.get('identified_algorithm', mapping.get('algorithm', 'Unknown'))
            await event_callback({"type": "success", "agent": "Translator", "status": f"Problem mapped to: {algo}"})
            self.session_manager.checkpoint(session_id, "TRANSLATED", {"mapping": mapping})

        await self._emit_content_chunk(
            event_callback,
            agent="Translator",
            content_type="text",
            content=mapping.get("story_explanation", ""),
            label="Quantum story context",
        )
        _save_json(os.path.join(run_dir, "mapping.json"), mapping)

        # --- STEP 2-4: ARCHITECTURE & VALIDATION LOOP ---
        attempt = session_data.get("attempt", 0) if resuming else 0
        validated_code = None
        scientific_report = session_data.get("scientific_report") if resuming else None
        evaluator_report = session_data.get("evaluator_report") if resuming else None
        result_diagram_b64 = session_data.get("result_diagram_b64") if resuming else ""
        nisq_warning = session_data.get("nisq_warning") if resuming else None
        actual_results = session_data.get("actual_results", {}) if resuming else {}

        # Determine where to resume inside the loop
        skip_architect = resuming and self._past_stage(resume_stage, "ARCHITECTED")
        skip_scientist = resuming and self._past_stage(resume_stage, "AUDITED")
        skip_evaluator = resuming and self._past_stage(resume_stage, "EVALUATED")

        # If fully evaluated, skip the entire loop
        if skip_evaluator:
            validated_code = session_data.get("code_package", {})
            evaluator_report = session_data.get("evaluator_report", {})
            result_diagram_b64 = session_data.get("result_diagram_b64", "")
            actual_results = session_data.get("actual_results", {})
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
                    await asyncio.sleep(1)
                    code_package = await asyncio.to_thread(self.architect.generate_code, mapping, scientific_report)
                    if 'error' in code_package:
                        await event_callback({"type": "error", "agent": "Architect", "status": f"Architect error: {code_package['error']}"})
                        continue

                    python_code = code_package.get('python_code', code_package.get('code', ''))
                    await event_callback({"type": "success", "agent": "Architect", "status": "Circuit generated successfully."})
                    _save_json(os.path.join(run_dir, f"code_package_attempt_{attempt}.json"), code_package)
                    _save_text(os.path.join(run_dir, f"qiskit_code_attempt_{attempt}.py"), python_code)
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
                    await asyncio.sleep(1)
                    scientific_report = await asyncio.to_thread(self.scientist.validate_proposal, mapping, python_code)

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
                            "code_package": code_package,
                        }, attempt=attempt)
                        _save_json(os.path.join(run_dir, f"scientific_report_attempt_{attempt}.json"), scientific_report)

                        # Scientist approved — proceed to Evaluator
                        pass
                    else:
                        feedback = scientific_report.get('architect_feedback', scientific_report.get('feedback', 'No detailed feedback'))
                        await event_callback({"type": "error", "agent": "Scientist", "status": f"Rejected. Reason: {feedback}"})
                        continue

                # --- EVALUATOR ---
                await event_callback({"type": "progress", "agent": "Evaluator", "status": "Running local simulation & final evaluation..."})
                await asyncio.sleep(1)

                actual_results = {"status": "FAILED", "histogram": {}}
                result_diagram_b64 = ""

                try:
                    actual_results = await asyncio.to_thread(_simulate_python_code, python_code)
                    if actual_results.get("error"):
                        await event_callback({"type": "warning", "agent": "Environment", "status": f"Sim execution failed: {actual_results['error']}"})
                except Exception as e:
                    actual_results["error"] = str(e)
                    await event_callback({"type": "warning", "agent": "Environment", "status": f"Code run hit error: {e}"})

                evaluator_report = await asyncio.to_thread(self.evaluator.evaluate_simulation, python_code, actual_results)
                _save_json(os.path.join(run_dir, f"simulation_results_attempt_{attempt}.json"), actual_results)
                _save_json(os.path.join(run_dir, f"evaluator_report_attempt_{attempt}.json"), evaluator_report)

                verdict = evaluator_report.get('verdict', 'FAIL')
                if verdict == 'PASS':
                    validated_code = code_package
                    await event_callback({"type": "success", "agent": "Evaluator", "status": "Evaluator Validation Passed."})
                    
                    # Generate Result Diagram if histogram exists
                    if actual_results.get("histogram"):
                        try:
                            result_diagram_b64 = await asyncio.to_thread(
                                _generate_histogram_diagram_b64,
                                actual_results["histogram"],
                            )
                            await self._emit_content_chunk(
                                event_callback,
                                agent="Environment",
                                content_type="image",
                                content=result_diagram_b64,
                                mime_type="image/png",
                                label="Simulation histogram",
                            )
                        except Exception as e:
                            print(f"Failed to generate result diagram: {e}")

                    self.session_manager.checkpoint(session_id, "EVALUATED", {
                        "evaluator_report": evaluator_report,
                        "code_package": code_package,
                        "result_diagram_b64": result_diagram_b64,
                        "actual_results": actual_results,
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
        python_code = validated_code.get("python_code", validated_code.get("code", ""))
        await event_callback({"type": "progress", "agent": "MediaProducer", "status": "Generating multimedia brief (audio + Imagen + Veo prompts)..."})
        await asyncio.sleep(1)
        visual_brief = await asyncio.to_thread(self.media_producer.generate_visuals, mapping, python_code)

        if visual_brief.get("error"):
            await event_callback(
                {
                    "type": "warning",
                    "agent": "MediaProducer",
                    "status": f"Prompt brief generation failed: {visual_brief['error']}",
                }
            )
            visual_brief = {}
        else:
            await event_callback({"type": "success", "agent": "MediaProducer", "status": "Cinematic visual briefs generated."})
        _save_json(os.path.join(run_dir, "visual_brief.json"), visual_brief)

        # --- STEP 6: ASSET GENERATION ---
        await event_callback({"type": "progress", "agent": "Environment", "status": "Generating image/video/audio assets..."})

        circuit_b64 = ""
        audio_b64 = ""
        audio_mime = "audio/wav"
        generated_illustration_b64 = ""
        generated_illustration_mime = "image/png"
        generated_video_b64 = ""
        generated_video_mime = "video/mp4"
        generated_video_uri = ""

        audio_script = visual_brief.get("audio_script", "")
        if audio_script:
            try:
                tts_audio = await asyncio.to_thread(
                    self.media_producer.generate_contextual_narration_audio,
                    mapping,
                    audio_script,
                )
                _save_json(os.path.join(run_dir, "tts_response.json"), tts_audio)
                if tts_audio.get("error"):
                    await event_callback(
                        {
                            "type": "warning",
                            "agent": "Environment",
                            "status": f"Gemini TTS generation failed: {tts_audio['error']}",
                        }
                    )
                else:
                    audio_b64 = tts_audio.get("data", "")
                    audio_mime = tts_audio.get("mime_type", "audio/wav")
                    await self._emit_content_chunk(
                        event_callback,
                        agent="Environment",
                        content_type="audio",
                        content=audio_b64,
                        mime_type=audio_mime,
                        label="Narrative audio",
                    )
            except Exception as e:
                await event_callback({"type": "warning", "agent": "Environment", "status": f"Audio generation failed: {str(e)}"})

        try:
            circuit_b64 = await asyncio.to_thread(_render_circuit_diagram_b64, python_code)
            if circuit_b64:
                await self._emit_content_chunk(
                    event_callback,
                    agent="Environment",
                    content_type="image",
                    content=circuit_b64,
                    mime_type="image/png",
                    label="Qiskit circuit diagram",
                )
        except Exception as e:
            await event_callback({"type": "warning", "agent": "Environment", "status": f"Circuit diagram generation failed: {str(e)}"})

        imagen_prompt = visual_brief.get("imagen_graphic_prompt", "")
        if imagen_prompt:
            imagen_response = await asyncio.to_thread(self.media_producer.generate_imagen_image, imagen_prompt)
            _save_json(os.path.join(run_dir, "imagen_response.json"), imagen_response)
            if imagen_response.get("error"):
                await event_callback(
                    {
                        "type": "warning",
                        "agent": "MediaProducer",
                        "status": f"Imagen generation skipped: {imagen_response['error']}",
                    }
                )
            else:
                generated_illustration_b64 = imagen_response.get("data", "")
                generated_illustration_mime = imagen_response.get("mime_type", "image/png")
                await self._emit_content_chunk(
                    event_callback,
                    agent="MediaProducer",
                    content_type="image",
                    content=generated_illustration_b64,
                    mime_type=generated_illustration_mime,
                    label="Imagen conceptual illustration",
                )

        veo_video_prompt = visual_brief.get("veo_video_prompt", visual_brief.get("video_prompt", ""))
        if veo_video_prompt:
            veo_response = await asyncio.to_thread(self.media_producer.generate_veo_video, veo_video_prompt)
            _save_json(os.path.join(run_dir, "veo_response.json"), veo_response)
            if veo_response.get("error"):
                await event_callback(
                    {
                        "type": "warning",
                        "agent": "MediaProducer",
                        "status": f"Veo generation skipped: {veo_response['error']}",
                    }
                )
            else:
                generated_video_b64 = veo_response.get("data", "")
                generated_video_mime = veo_response.get("mime_type", "video/mp4")
                generated_video_uri = veo_response.get("uri", "")
                if generated_video_b64:
                    await self._emit_content_chunk(
                        event_callback,
                        agent="MediaProducer",
                        content_type="video",
                        content=generated_video_b64,
                        mime_type=generated_video_mime,
                        label="Veo generated video",
                    )

        await event_callback({"type": "success", "agent": "Environment", "status": "Media assets successfully compiled."})


        # FINAL OUTPUT ASSEMBLY
        mapping_summary = {
            "problem_class": mapping.get("problem_class", "Unknown"),
            "identified_algorithm": mapping.get("identified_algorithm", mapping.get("algorithm", "Unknown")),
            "why_this_algorithm": mapping.get("mathematical_justification", ""),
            "how_user_problem_maps": mapping.get("story_explanation", ""),
        }
        final_package = {
            "metadata": {
                "algorithm": mapping.get('identified_algorithm', mapping.get('algorithm', 'Unknown')),
                "qubits": mapping.get('qubit_requirement_estimate', mapping.get('qubits', 0))
            },
            "problem_algorithm_mapping": mapping_summary,
            "quantum_story_context": mapping.get('story_explanation', ''),
            "complete_code": python_code,
            "algorithm_explanation": validated_code.get('explanation', ''),
            "video_prompt": veo_video_prompt,
            "imagen_graphic_prompt": imagen_prompt,
            "qiskit_circuit_diagram": circuit_b64,
            "generated_illustration": generated_illustration_b64,
            "generated_illustration_mime": generated_illustration_mime,
            "generated_video": generated_video_b64,
            "generated_video_mime": generated_video_mime,
            "generated_video_uri": generated_video_uri,
            "result_diagram": result_diagram_b64,
            "narrative_audio": audio_b64,
            "narrative_audio_mime": audio_mime,
            "simulation_results": actual_results,
            "nisq_warning": nisq_warning,
            "evaluator_report": evaluator_report,
        }

        _save_json(os.path.join(run_dir, "final_package.json"), final_package)
        _save_text(os.path.join(run_dir, "complete_qiskit_code.py"), python_code)
        _save_json(os.path.join(run_dir, "problem_algorithm_mapping.json"), mapping_summary)

        if circuit_b64:
            _save_base64_file(os.path.join(run_dir, "qiskit_circuit_diagram.png"), circuit_b64)
        if result_diagram_b64:
            _save_base64_file(os.path.join(run_dir, "simulation_histogram.png"), result_diagram_b64)
        if generated_illustration_b64:
            _save_base64_file(
                os.path.join(run_dir, f"generated_illustration{_ext_from_mime(generated_illustration_mime)}"),
                generated_illustration_b64,
            )
        if generated_video_b64:
            _save_base64_file(
                os.path.join(run_dir, f"generated_video{_ext_from_mime(generated_video_mime)}"),
                generated_video_b64,
            )
        if audio_b64:
            _save_base64_file(
                os.path.join(run_dir, f"narrative_audio{_ext_from_mime(audio_mime)}"),
                audio_b64,
            )

        # Mark session as COMPLETED and clean up
        self.session_manager.checkpoint(session_id, "COMPLETED", {})
        self.session_manager.delete_session(session_id)

        await event_callback({"type": "complete", "agent": "Orchestrator", "status": "Final Multimodal Package Ready!", "data": final_package})
        return final_package

app = FastAPI()

cors_origins = _parse_allowed_origins()
allow_credentials = cors_origins != ["*"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=allow_credentials,
    allow_methods=["*"],
    allow_headers=["*"],
)

session_manager = SessionManager()
orchestrator = QuantumOrchestrator()
active_workflows_by_ip: Dict[str, int] = {}
active_workflows_lock = asyncio.Lock()


async def _acquire_workflow_slot(client_ip: str) -> bool:
    async with active_workflows_lock:
        active_count = active_workflows_by_ip.get(client_ip, 0)
        if active_count >= MAX_ACTIVE_WORKFLOWS_PER_IP:
            return False
        active_workflows_by_ip[client_ip] = active_count + 1
        return True


async def _release_workflow_slot(client_ip: str) -> None:
    async with active_workflows_lock:
        active_count = active_workflows_by_ip.get(client_ip, 0)
        if active_count <= 1:
            active_workflows_by_ip.pop(client_ip, None)
        else:
            active_workflows_by_ip[client_ip] = active_count - 1


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
    client_ip = websocket.client.host if websocket.client else "unknown"
    slot_acquired = await _acquire_workflow_slot(client_ip)
    if not slot_acquired:
        await websocket.send_json(
            {
                "type": "fatal",
                "agent": "Server",
                "status": "Rate limit hit: only one active workflow is allowed per IP.",
            }
        )
        await websocket.close(code=1013)
        return

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

        prompt = (prompt or "").strip()
        if not prompt:
            await websocket.send_json(
                {
                    "type": "fatal",
                    "agent": "Server",
                    "status": "Prompt is empty. Please provide a quantum problem statement.",
                }
            )
            return
        if len(prompt) > MAX_PROMPT_LENGTH:
            await websocket.send_json(
                {
                    "type": "fatal",
                    "agent": "Server",
                    "status": (
                        f"Prompt too long ({len(prompt)} chars). Maximum allowed is "
                        f"{MAX_PROMPT_LENGTH} characters."
                    ),
                }
            )
            return

        async def send_event_to_ws(event: dict):
            await websocket.send_json(event)
            await asyncio.sleep(0.05)

        await orchestrator.run_workflow(prompt, send_event_to_ws, session_id=session_id)

    except WebSocketDisconnect:
        print("Client disconnected.")
    except Exception as e:
        print(f"Error during simulation: {e}")
        await websocket.send_json({"type": "fatal", "agent": "Server", "status": str(e)})
    finally:
        await _release_workflow_slot(client_ip)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
