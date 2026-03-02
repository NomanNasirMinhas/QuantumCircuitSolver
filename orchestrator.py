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
        
        # Internal state to track the conversation
        self.session_history = []
        self.max_retries = 3

    def run_workflow(self, user_input: str) -> Dict[str, Any]:
        print(f"--- Starting Quantum Workflow for: '{user_input}' ---")
        
        # STEP 1: TRANSLATION (Plain Text -> Quantum Mapping)
        time.sleep(2)  # Pause to avoid Gemini API rate limits
        mapping = self.translator.map_problem(user_input)
        
        if 'error' in mapping:
             return {"error": "Translation failed", "details": mapping}
             
        # Fallbacks if keys are slightly different
        algo = mapping.get('identified_algorithm', mapping.get('algorithm', 'Unknown'))
        
        print(f"[1] Problem mapped to: {algo}")

        # STEP 2: ARCHITECTURE & VALIDATION LOOP (The Self-Healing Core)
        attempt = 0
        validated_code = None
        scientific_report = None
        evaluator_report = None

        while attempt < self.max_retries:
            attempt += 1
            print(f"[2] Architecture Attempt {attempt}...")
            
            # Generate Qiskit Code
            time.sleep(5)  # Pause to avoid rate limit
            code_package = self.architect.generate_code(mapping, feedback=scientific_report)
            if 'error' in code_package:
                print(f"[!] Architect error: {code_package['error']}")
                continue
                
            python_code = code_package.get('python_code', code_package.get('code', ''))
            
            # STEP 3: SCIENTIFIC AUDIT (The Scientist Agent)
            print(f"[3] Scientist Agent auditing code...")
            time.sleep(5)  # Pause to avoid rate limit
            scientific_report = self.scientist.validate_proposal(mapping, python_code)
            
            decision = scientific_report.get('decision', 'REJECTED')
            
            if decision == "APPROVED":
                print(">>> SUCCESS: Scientific Validation Passed.")
                
                # STEP 4: EVALUATOR AUDIT
                print(f"[4] Evaluator Agent performing final validation...")
                time.sleep(5)  # Pause to avoid rate limit
                
                # Execute the Qiskit code locally to get actual simulation results
                print("    [*] Executing Qiskit code to generate simulation results...")
                actual_results = {"status": "FAILED", "histogram": {}}
                
                try:
                    with open("temp_circuit.py", "w") as f:
                        f.write(python_code)
                    
                    # Run the script and capture stdout
                    import sys # Ensure python executable is correct
                    python_exe = sys.executable 
                    # If we are in a venv, sys.executable is the venv python.
                    
                    result = subprocess.run([python_exe, "temp_circuit.py"], capture_output=True, text=True, timeout=60)
                    
                    if result.returncode == 0:
                        actual_results["status"] = "COMPLETED"
                        # Simple extraction: find the last printed dictionary (the histogram)
                        output = result.stdout.strip()
                        try:
                            # Try to extract the dictionary like {"0000": 100, "1111": 924}
                            dict_str_start = output.rfind('{')
                            dict_str_end = output.rfind('}')
                            if dict_str_start != -1 and dict_str_end != -1 and dict_str_end > dict_str_start:
                                dict_str = output[dict_str_start:dict_str_end+1]
                                # Evaluate safely
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
                        actual_results["error"] = result.stderr.strip().split('\n')[-3:] # Capture last 3 lines
                        print(f"    [!] Code execution failed: {actual_results['error']}")
                except Exception as e:
                    actual_results["error"] = str(e)
                    print(f"    [!] Error running code: {e}")
                finally:
                    if os.path.exists("temp_circuit.py"):
                        os.remove("temp_circuit.py")

                evaluator_report = self.evaluator.evaluate_simulation(python_code, actual_results)
                
                verdict = evaluator_report.get('verdict', 'FAIL')
                if verdict == 'PASS':
                    validated_code = code_package
                    print(">>> SUCCESS: Evaluator Validation Passed.")
                    break
                else:
                    print(f">>> FAIL: Evaluator rejected code. Reason: {evaluator_report.get('validation_summary', '')}")
                    # Feed evaluator feedback back to architect in loop (as 'scientific_report' to reuse the feedback variable)
                    scientific_report = {"decision": "REJECTED", "architect_feedback": evaluator_report.get('feedback_for_agents', 'Syntax or logic error.')}
            else:
                feedback = scientific_report.get('architect_feedback', scientific_report.get('feedback', 'No detailed feedback'))
                print(f">>> FAIL: Scientist rejected code. Reason: {feedback}")

        if not validated_code:
            return {"error": "Could not generate a scientifically valid circuit after 3 attempts."}

        # STEP 5: MEDIA PRODUCTION (Visuals & Narratives)
        print(f"[5] Media Producer generating cinematic assets...")
        time.sleep(5)  # Pause to avoid rate limit
        visual_brief = self.media_producer.generate_visuals(mapping, validated_code.get('python_code', validated_code.get('code', '')))

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

        return final_package

# --- GEMINI LIVE INTEGRATION MOCK ---
def on_user_voice_input(voice_text):
    orchestrator = QuantumOrchestrator()
    result = orchestrator.run_workflow(voice_text)
    
    # In a real app, you would now:
    # 1. Play 'audio_narration' via Gemini Live TTS.
    # 2. Trigger Veo/Imagen APIs using the generated prompts.
    # 3. Display the Qiskit code in the UI terminal.
    print("\n--- FINAL MULTIMODAL PACKAGE READY ---")
    print(json.dumps(result, indent=2))

if __name__ == "__main__":
    on_user_voice_input("I have 200 computers in my network and I want to find the lowest effort path for an attacker to break into my network.")