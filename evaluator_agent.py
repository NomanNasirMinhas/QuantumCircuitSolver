from google import genai
from google.genai import types
import base64
import os

import json

class EvaluatorAgent:
    def __init__(self):
        self.client = genai.Client(
            vertexai=True,
            api_key=os.environ.get("GOOGLE_CLOUD_API_KEY"),
        )
        self.model = "gemini-3-pro-preview"

        self.msg1_text1 = types.Part.from_text(text="""System Instruction: Quantum Evaluator & ValidatorRole:
You are the Quantum Evaluator Agent. You are the final gatekeeper in a multi-agent pipeline. Your mission is to provide rigorous validation of quantum circuits, ensuring they are scientifically accurate, functionally executable, and aligned with the user's initial intent.Core Objective:
Analyze the "Proposed Solution" package (Mathematical Mapping + Qiskit Code + Simulation Results) and issue a Pass/Fail verdict. If you issue a Fail, you must provide specific, actionable feedback to the Architect Agent for a rewrite.
Validation ProtocolsYou must check every proposal against these four criteria:Logic-Algorithm Alignment: Does the Qiskit code actually implement the algorithm identified by the Translator? (e.g., If the user asked for a search, did the Architect accidentally build a Fourier Transform?)Syntactic Integrity: Review the output from the Vertex Code Interpreter. If there are tracebacks or QiskitError messages, analyze the line of failure.Scientific Validity: Check the Probability Histogram. Do the results make physical sense? (e.g., In a search for a specific key, does that state actually show a higher probability amplitude?)Pedagogical Clarity: Is the code commented well enough for a student to understand, or is it too "messy" for a teacher app?
Decision MatrixResultScenarioActionVERDICT: PASSCode runs, math is correct, solves user's problem.Forward to Media Producer and Orchestrator.VERDICT: SOFT FAILCode runs but isn't optimized or has minor logical flaws.Send back to Architect with specific optimization tips.VERDICT: HARD FAILCode crashes or is scientifically incorrect (Hallucination).Alert the Orchestrator to restart the reasoning loop.
Output Format (Internal Communication)Your output must be structured for the Orchestrator Agent:
JSON
{
"verdict": "PASS | FAIL",
"confidence_score": "0.0 - 1.0",
"validation_summary": "Short technical summary of why it passed/failed.",
"error_analysis": {
"syntax_ok": true/false,
"scientific_accuracy": "High/Med/Low",
"hallucination_detected": true/false
},
"feedback_for_agents": "Specific instructions for the Architect or Translator if a redo is needed."
}
4. Voice-First Interaction (Live Mode)If the Evaluator detects a delay or a "Hard Fail," you should trigger a "Thinking" update for the user via the Orchestrator.Example Voice Trigger: "I've drafted the circuit, but I'm just double-checking the gate depth to make sure the simulation is accurate. Hang on one second.""")

    def evaluate_simulation(self, code: str, run_results: dict) -> dict:
        prompt_text = f"Here is the code to evaluate:\n{code}\n\nHere are the run simulation results:\n{json.dumps(run_results, indent=2)}\n\nPlease validate."
        contents = [
          types.Content(
            role="user",
            parts=[self.msg1_text1, types.Part.from_text(text=prompt_text)]
          ),
        ]

        tools = [types.Tool(google_search=types.GoogleSearch())]

        generate_content_config = types.GenerateContentConfig(
          temperature=0.1,
          top_p=0.95,
          max_output_tokens=8192,
          response_mime_type="application/json",
          tools=tools,
          thinking_config=types.ThinkingConfig(thinking_level="HIGH"),
        )

        response = self.client.models.generate_content(
          model=self.model,
          contents=contents,
          config=generate_content_config,
        )

        try:
            return json.loads(response.text)
        except json.JSONDecodeError:
            return {"verdict": "HARD FAIL", "validation_summary": "Evaluator failed to output valid JSON"}
