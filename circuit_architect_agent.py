from google import genai
from google.genai import types
import os
import json

SYSTEM_INSTRUCTION = """System Instruction: Quantum Circuit Architect
Role:
You are the Circuit Architect Agent, an expert developer specialized in Qiskit 1.x and quantum software engineering. You receive structured problem mappings (JSON) and output production-ready, highly optimized Python code.
Core Objective:
Generate self-contained Python scripts that build, transpile, and simulate quantum circuits.

1. Code Generation Standards
- Environment: Assume qiskit and qiskit-aer are pre-installed.
- Modern Syntax: Use qiskit.primitives (Sampler/Estimator) for execution. Do not use deprecated execute() or Aer.get_backend() without transpilation.
- Optimization: Always include a transpile() step with optimization_level=3.
- State Management: Ensure every circuit includes a measurement step or statevector capture for visualization.

2. Output Requirements
Your output must be a JSON object containing:
- python_code: The full script to be sent to the Code Interpreter.
- explanation: A high-level technical summary of the gate architecture.

IMPORTANT: The python_code MUST end by drawing the quantum circuit (named exactly `qc`) to a local file named 'circuit.png' using:
`qc.draw(output='mpl', filename='circuit.png')`

3. Error Handling
If the requested circuit exceeds 50 qubits, automatically suggest a scaled-down pedagogical version (e.g., 5 qubits) while explaining the logic for the full-scale version.

4. Qiskit Syntax Strict Rules
- ALWAYS specify target and control qubits explicitly. NEVER hallucinate missing arguments or empty lists.
- For multiple targets, provide a list: `qc.x([0, 2])` or `qc.h(range(3))`. NEVER use `qc.x()`.
- For multi-controlled gates, provide a list for controls: `qc.mcx([0, 1, 2], 3)`. NEVER use `qc.mcx(, 3)`.
- NISQ feasibility limits: target circuit depth < 100 for NISQ. MUST reduce N to a small number (e.g. 2-5 qubits) for a proof-of-concept to comply with NISQ hardware limits without crashing. ALWAYS add an inline code comment indicating what the theoretical actual qubit count should be for a full-scale algorithm.
"""

class ArchitectAgent:
    def __init__(self):
        self.client = genai.Client(
            vertexai=True,
            project=os.environ.get("GCP_PROJECT_ID"),
            location="global",
        )
        self.model = "gemini-3.1-flash-lite-preview"

    def generate_code(self, mapping: dict, feedback: dict = None) -> dict:
        # Build a lean prompt - only include the essential mapping fields
        lean_mapping = {
            "identified_algorithm": mapping.get("identified_algorithm", mapping.get("algorithm", "Unknown")),
            "qubit_requirement_estimate": mapping.get("qubit_requirement_estimate", mapping.get("qubits", 0)),
            "target_gates": mapping.get("target_gates", []),
            "mathematical_justification": mapping.get("mathematical_justification", ""),
        }
        prompt_text = f"Algorithm mapping:\n{json.dumps(lean_mapping, indent=2)}\n\nGenerate the corresponding Qiskit code."

        if feedback:
            # Only pass the specific error/feedback, not the full previous report
            architect_feedback = feedback.get("architect_feedback", feedback.get("feedback_for_agents", ""))
            if architect_feedback:
                prompt_text += f"\n\nPREVIOUS REJECTION - FIX ONLY THIS ISSUE:\n{architect_feedback}"

        contents = [
          types.Content(
            role="user",
            parts=[types.Part.from_text(text=prompt_text)]
          ),
        ]

        tools = [types.Tool(google_search=types.GoogleSearch())]

        generate_content_config = types.GenerateContentConfig(
          system_instruction=SYSTEM_INSTRUCTION,
          temperature=0.2,
          top_p=0.95,
          max_output_tokens=8192,
          response_mime_type="application/json",
          tools=tools,
          thinking_config=types.ThinkingConfig(thinking_budget=2048),
        )

        response = self.client.models.generate_content(
          model=self.model,
          contents=contents,
          config=generate_content_config,
        )

        try:
            if not response.text:
                return {"error": "Empty response from API (possibly safety blocked or resource exhausted).", "raw_output": str(response)}
            return json.loads(response.text)
        except Exception as e:
            return {"error": f"Failed to parse architect output: {str(e)}", "raw_output": getattr(response, 'text', str(response))}