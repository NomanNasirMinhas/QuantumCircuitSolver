from google import genai
from google.genai import types
import base64
import os

def generate():
  client = genai.Client(
      vertexai=True,
      api_key=os.environ.get("GOOGLE_CLOUD_API_KEY"),
  )

  msg1_text1 = types.Part.from_text(text="""System Instruction: Quantum Circuit ArchitectRole:
You are the Circuit Architect Agent, an expert developer specialized in Qiskit 1.x and quantum software engineering. You receive structured problem mappings (JSON) and output production-ready, highly optimized Python code.Core Objective:
Generate self-contained Python scripts that build, transpile, and simulate quantum circuits. Your code must be compatible with the Vertex Code Execution environment.
1. Code Generation StandardsEnvironment: Always include pip install qiskit qiskit-aer in your execution logic or assume a pre-configured environment.Modern Syntax: Use the qiskit.primitives (Sampler/Estimator) for execution. Do not use deprecated execute() or Aer.get_backend() without transpilation.Optimization: Always include a transpile() step with optimization_level=3.State Management: Ensure every circuit includes a measurement step or statevector capture for visualization.
2. Output RequirementsYour output must be a JSON object containing:python_code: The full script to be sent to the Code Interpreter.explanation: A high-level technical summary of the gate architecture (e.g., \"Applying a layer of $R_y$ gates for state preparation\").visualization_hints: Specific keywords (e.g., \"entanglement\", \"interference\") for the Media Producer Agent to use in video generation.
3. Error HandlingIf the requested circuit exceeds 50 qubits (simulatable limit), you must automatically suggest a scaled-down pedagogical version (e.g., 5 qubits) while explaining the logic for the full-scale version.
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

  model = "gemini-3.1-pro-preview"
  contents = [
    types.Content(
      role="user",
      parts=[
        msg1_text1
      ]
    ),
  ]
  tools = [
    types.Tool(google_search=types.GoogleSearch()),
  ]

  generate_content_config = types.GenerateContentConfig(
    temperature = 1,
    top_p = 0.95,
    max_output_tokens = 65535,
    safety_settings = [types.SafetySetting(
      category="HARM_CATEGORY_HATE_SPEECH",
      threshold="OFF"
    ),types.SafetySetting(
      category="HARM_CATEGORY_DANGEROUS_CONTENT",
      threshold="OFF"
    ),types.SafetySetting(
      category="HARM_CATEGORY_SEXUALLY_EXPLICIT",
      threshold="OFF"
    ),types.SafetySetting(
      category="HARM_CATEGORY_HARASSMENT",
      threshold="OFF"
    )],
    tools = tools,
    thinking_config=types.ThinkingConfig(
      thinking_level="HIGH",
    ),
  )

  for chunk in client.models.generate_content_stream(
    model = model,
    contents = contents,
    config = generate_content_config,
    ):
    if not chunk.candidates or not chunk.candidates[0].content or not chunk.candidates[0].content.parts:
        continue
    print(chunk.text, end="")

generate()