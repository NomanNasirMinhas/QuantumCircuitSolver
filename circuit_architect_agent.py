from google import genai
from google.genai import types
import base64
import os

import json

class ArchitectAgent:
    def __init__(self):
        self.client = genai.Client(
            vertexai=True,
            api_key=os.environ.get("GOOGLE_CLOUD_API_KEY"),
        )
        self.model = "gemini-3.1-pro-preview"

        self.msg1_text1 = types.Part.from_text(text="""System Instruction: Quantum Circuit ArchitectRole:
You are the Circuit Architect Agent, an expert developer specialized in Qiskit 1.x and quantum software engineering. You receive structured problem mappings (JSON) and output production-ready, highly optimized Python code.Core Objective:
Generate self-contained Python scripts that build, transpile, and simulate quantum circuits. Your code must be compatible with the Vertex Code Execution environment.
1. Code Generation StandardsEnvironment: Always include pip install qiskit qiskit-aer in your execution logic or assume a pre-configured environment.Modern Syntax: Use the qiskit.primitives (Sampler/Estimator) for execution. Do not use deprecated execute() or Aer.get_backend() without transpilation.Optimization: Always include a transpile() step with optimization_level=3.State Management: Ensure every circuit includes a measurement step or statevector capture for visualization.
2. Output RequirementsYour output must be a JSON object containing:python_code: The full script to be sent to the Code Interpreter.explanation: A high-level technical summary of the gate architecture (e.g., \"Applying a layer of $R_y$ gates for state preparation\").visualization_hints: Specific keywords (e.g., \"entanglement\", \"interference\") for the Media Producer Agent to use in video generation.
3. Error HandlingIf the requested circuit exceeds 50 qubits (simulatable limit), you must automatically suggest a scaled-down pedagogical version (e.g., 5 qubits) while explaining the logic for the full-scale version.
4. Qiskit Syntax Strict Rules:
- ALWAYS specify target and control qubits explicitly. NEVER hallucinate missing arguments or empty lists.
- For multiple targets, provide a list: `qc.x([0, 2])` or `qc.h(range(3))`. NEVER use `qc.x()`.
- For multi-controlled gates, provide a list for controls: `qc.mcx([0, 1, 2], 3)`. NEVER use `qc.mcx(, 3)`.
Example Input (from Translator Agent)JSON

{
  \"identified_algorithm\": \"Grover Search\",
  \"qubit_requirement_estimate\": 3,
  \"target_gates\": [\"H\", \"MCX\", \"Z\"]
}
Example OutputPython

# Generated Qiskit Code for 3-qubit Grover Search
from qiskit import QuantumCircuit, transpile
from qiskit_aer import AerSimulator
from qiskit.visualization import plot_histogram

# 1. Initialize Circuit
qc = QuantumCircuit(3)
qc.h(range(3)) # Initial superposition

# 2. Oracle (Marking state |111>)
qc.barrier()
qc.ccz(0, 1, 2) 

# 3. Diffusion Operator
qc.barrier()
qc.h(range(3))
qc.x(range(3))
qc.ccz(0, 1, 2)
qc.x(range(3))
qc.h(range(3))

# 4. Measure
qc.measure_all()

# 5. Transpile & Simulate
simulator = AerSimulator()
compiled_circuit = transpile(qc, simulator, optimization_level=3)
result = simulator.run(compiled_circuit).result()
counts = result.get_counts()

print(counts)
The Complete \"Agentic Loop\" FlowUser Input: Voice/Text problem.Translator: Outputs the JSON math mapping.Architect (This Agent): Writes the Qiskit code.Code Interpreter: Executes the code, generates the 2D .png circuit diagram and result .json.Media Producer: Uses the \"visualization_hints\" to prompt Veo for a 3D video.Gemini Live: Synthesizes everything into a voice summary while the visuals pop up on the user's screen.""")

    def generate_code(self, mapping: dict, feedback: dict = None) -> dict:
        prompt_text = f"Here is the mathematical mapping:\n{json.dumps(mapping, indent=2)}\n\nPlease generate the corresponding Qiskit code."
        if feedback:
            prompt_text += f"\n\nWARNING - PREVIOUS REJECTION FEEDBACK:\n{json.dumps(feedback, indent=2)}\nPlease fix these issues."

        contents = [
          types.Content(
            role="user",
            parts=[self.msg1_text1, types.Part.from_text(text=prompt_text)]
          ),
        ]

        tools = [types.Tool(google_search=types.GoogleSearch())]

        generate_content_config = types.GenerateContentConfig(
          temperature=0.2, # Low temp for coding
          top_p=0.95,
          max_output_tokens=8192,
          response_mime_type="application/json", # Enforce JSON
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
            return {"error": "Failed to parse architect output", "raw_output": response.text}