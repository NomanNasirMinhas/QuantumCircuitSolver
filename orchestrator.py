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

class QuantumOrchestrator:
    def __init__(self):
        self.translator = TranslatorAgent()
        self.architect = ArchitectAgent()
        self.scientist = ScientistAgent()
        self.evaluator = EvaluatorAgent()
        self.media_producer = MediaProducerAgent()
        self.max_retries = 3

    async def run_workflow(self, user_input: str, event_callback) -> Dict[str, Any]:
        await event_callback({"type": "progress", "agent": "Orchestrator", "status": f"Starting Quantum Workflow for: '{user_input}'"})
        
        # STEP 1: TRANSLATION (Plain Text -> Quantum Mapping)
        await event_callback({"type": "progress", "agent": "Translator", "status": "Translating natural language to quantum problem mapping..."})
        time.sleep(2)
        mapping = self.translator.map_problem(user_input)
        
        if 'error' in mapping:
             await event_callback({"type": "error", "agent": "Translator", "status": "Translation failed", "details": mapping})
             return {"error": "Translation failed", "details": mapping}
             
        algo = mapping.get('identified_algorithm', mapping.get('algorithm', 'Unknown'))
        await event_callback({"type": "success", "agent": "Translator", "status": f"Problem mapped to: {algo}"})

        # STEP 2: ARCHITECTURE & VALIDATION LOOP
        attempt = 0
        validated_code = None
        scientific_report = None
        evaluator_report = None

        while attempt < self.max_retries:
            attempt += 1
            await event_callback({"type": "progress", "agent": "Architect", "status": f"Architecture Generation (Attempt {attempt})..."})
            
            time.sleep(5)
            code_package = self.architect.generate_code(mapping, feedback=scientific_report)
            if 'error' in code_package:
                await event_callback({"type": "error", "agent": "Architect", "status": f"Architect error: {code_package['error']}"})
                continue
                
            python_code = code_package.get('python_code', code_package.get('code', ''))
            await event_callback({"type": "success", "agent": "Architect", "status": "Circuit generated successfully."})
            
            # STEP 3: SCIENTIFIC AUDIT
            await event_callback({"type": "progress", "agent": "Scientist", "status": "Auditing proposed quantum circuit..."})
            time.sleep(5)
            scientific_report = self.scientist.validate_proposal(mapping, python_code)
            
            decision = scientific_report.get('decision', 'REJECTED')
            
            if decision == "APPROVED":
                await event_callback({"type": "success", "agent": "Scientist", "status": "Scientific validation passed."})
                
                # STEP 4: EVALUATOR AUDIT
                await event_callback({"type": "progress", "agent": "Evaluator", "status": "Running local simulation & final evaluation..."})
                time.sleep(5)
                
                actual_results = {"status": "FAILED", "histogram": {}}
                
                try:
                    with open("temp_circuit.py", "w") as f:
                        f.write(python_code)
                    
                    import sys
                    python_exe = sys.executable 
                    result = subprocess.run([python_exe, "temp_circuit.py"], capture_output=True, text=True, timeout=60)
                    
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
                        except Exception as parse_e:
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
                    break
                else:
                    reason = evaluator_report.get('validation_summary', '')
                    await event_callback({"type": "error", "agent": "Evaluator", "status": f"Rejected. Reason: {reason}"})
                    # Pass only the specific fix string - not the full report - to keep the retry prompt lean
                    fix_instructions = evaluator_report.get('feedback_for_agents', 'Syntax or logic error detected. Review and fix the circuit.')
                    scientific_report = {"decision": "REJECTED", "architect_feedback": fix_instructions}
            else:
                feedback = scientific_report.get('architect_feedback', scientific_report.get('feedback', 'No detailed feedback'))
                await event_callback({"type": "error", "agent": "Scientist", "status": f"Rejected. Reason: {feedback}"})

        if not validated_code:
            await event_callback({"type": "error", "agent": "Orchestrator", "status": "Could not generate a scientifically valid circuit after 3 attempts."})
            return {"error": "Could not generate a scientifically valid circuit after 3 attempts."}

        # STEP 5: MEDIA PRODUCTION
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
            "audio_narration": visual_brief.get('audio_script', '')
        }

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

@app.get("/")
def read_root():
    return {"message": "Quantum Orchestrator API is Live"}

@app.websocket("/ws/simulate")
async def websocket_simulate(websocket: WebSocket):
    await websocket.accept()
    orchestrator = QuantumOrchestrator()
    try:
        data = await websocket.receive_text()
        
        async def send_event_to_ws(event: dict):
            await websocket.send_json(event)
            # Yield control occasionally so WS buffer flushes
            await asyncio.sleep(0.1)

        result = await orchestrator.run_workflow(data, send_event_to_ws)
        
    except WebSocketDisconnect:
        print("Client disconnected.")
    except Exception as e:
        print(f"Error during simulation: {e}")
        await websocket.send_json({"type": "fatal", "agent": "Server", "status": str(e)})

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)