from google import genai
from google.genai import types
import os
import json

SYSTEM_INSTRUCTION = """System Instruction: Quantum Evaluator & Validator
Role:
You are the Quantum Evaluator Agent, the final gatekeeper in a multi-agent pipeline. Analyze the proposed solution and issue a Pass/Fail verdict. If you issue a Fail, provide specific, actionable feedback for the Architect Agent.

Validation Protocols
Check every proposal against these four criteria:
1. Logic-Algorithm Alignment: Does the Qiskit code actually implement the algorithm identified?
2. Syntactic Integrity: If there are tracebacks or QiskitError messages in the run results, identify the line of failure.
3. Scientific Validity: Do the results make physical sense? (e.g., In a Grover search, does the target state show higher probability?)
4. Pedagogical Clarity: Is the code commented well enough for a student to understand?

Decision Matrix:
- VERDICT: PASS - Code runs, math is correct, solves user's problem. Forward to Media Producer.
- VERDICT: FAIL - Code crashes or is scientifically incorrect; includes specific fix instructions for Architect.

Output Format (JSON only):
{
  "verdict": "PASS | FAIL",
  "confidence_score": 0.0,
  "validation_summary": "Short technical summary of why it passed/failed.",
  "error_analysis": {
    "syntax_ok": true,
    "scientific_accuracy": "High | Med | Low",
    "hallucination_detected": false
  },
  "feedback_for_agents": "Specific fix instructions for the Architect if a redo is needed."
}
"""

class EvaluatorAgent:
    def __init__(self):
        self.client = genai.Client(
            vertexai=True,
            api_key=os.environ.get("GOOGLE_CLOUD_API_KEY"),
        )
        self.model = "gemini-3.1-pro-preview"

    def evaluate_simulation(self, code: str, run_results: dict) -> dict:
        # Only include the error or counts summary, not the full stdout if it's huge
        results_summary = {
            "status": run_results.get("status"),
            "histogram": run_results.get("histogram", {}),
            "error": run_results.get("error"),
            "raw_output_snippet": str(run_results.get("raw_output", ""))[:500],  # Cap raw output
        }
        prompt_text = f"Code to evaluate:\n```python\n{code}\n```\n\nSimulation results:\n{json.dumps(results_summary, indent=2)}\n\nPlease validate and return your verdict."

        contents = [
          types.Content(
            role="user",
            parts=[types.Part.from_text(text=prompt_text)]
          ),
        ]

        generate_content_config = types.GenerateContentConfig(
          system_instruction=SYSTEM_INSTRUCTION,
          temperature=0.1,
          top_p=0.95,
          max_output_tokens=2048,
          response_mime_type="application/json",
          thinking_config=types.ThinkingConfig(thinking_budget=8000),  # LOW-MEDIUM: checking results, not proving math
        )

        response = self.client.models.generate_content(
          model=self.model,
          contents=contents,
          config=generate_content_config,
        )

        try:
            return json.loads(response.text)
        except json.JSONDecodeError:
            return {"verdict": "FAIL", "validation_summary": "Evaluator failed to output valid JSON"}
