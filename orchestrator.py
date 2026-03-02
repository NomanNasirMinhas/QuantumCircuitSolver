import json
import time
import os
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
                # Mock simulation results for validation
                dummy_results = {"status": "COMPLETED", "histogram": {"00": 0.1, "11": 0.9}}
                evaluator_report = self.evaluator.evaluate_simulation(python_code, dummy_results)
                
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