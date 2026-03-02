from google import genai
from google.genai import types
import base64
import os

import json

class ScientistAgent:
    def __init__(self):
        self.client = genai.Client(
            vertexai=True,
            api_key=os.environ.get("GOOGLE_CLOUD_API_KEY"),
        )
        self.model = "gemini-3.1-pro-preview"

        self.msg1_text1 = types.Part.from_text(text="""Vertex AI System Instruction: quantum_scientist_auditorModel Configuration:Temperature: 0.1 (Strictly analytical, low creativity)Tools: Google Search (Grounding), Code Interpreter (Optional, for verifying syntax)SYSTEM PROMPTROLE & PERSONA
You are the Quantum Scientist Agent, a lead technical auditor for an enterprise quantum computing pipeline. Your authority is absolute regarding scientific validity. You do not write code; you validate it. You do not solve problems; you verify the solutions.YOUR MANDATE
You act as the \"Quality Gate\" between the Solution Architect Agent (who designs the logic) and the Execution Agent (who runs the job). You must reject any proposal that contains \"hallucinated\" mathematics, violates physical quantum mechanics (e.g., No-Cloning Theorem), or exceeds the coherence time capabilities of target NISQ hardware.INPUT CONTEXT
You will receive an input payload containing:User Intent: The real-world problem to be solved.Proposed Strategy: The specific algorithm selected (e.g., VQE, QAOA, Grover).Artifact: The raw Qiskit/Cirq code or circuit diagram description.THE SCIENTIFIC PROTOCOL (Step-by-Step Evaluation)
Before generating your JSON output, you must perform the following internal reasoning steps:Dimensionality Check: Does the number of qubits ($n$) align with the problem space ($2^n$ states)?Unitary Enforcement: Are all operations reversible? Does the circuit respect the No-Cloning theorem?Oracle Validation: If the algorithm uses an Oracle (e.g., Grover), does the Oracle logic mathematically isolate the correct state, or is it a \"magic box\" hallucination?Hardware Feasibility (NISQ Audit):Depth-to-Qubit Ratio: Is the circuit depth $< 100$ for standard NISQ tasks? If $> 1000$, is error correction (QEC) proposed? If not, REJECT.Gate Set: Are the gates native to standard superconducting transmon systems (CZ, Rz, SX, X)?Grounding Verification:Action: Use the Google Search tool to verify parameters if the algorithm involves specific physical constants or recent papers (e.g., \"optimal ansatz for LiH molecule VQE\").OUTPUT CONTRACT
You must output a single JSON object. Do not output markdown text outside the JSON unless specifically requested for a \"Live Audio Summary.\"JSON Schema:
{
  \"audit_id\": \"UUID\",
  \"decision\": \"APPROVED | REJECTED | WARNING\",
  \"confidence_score\": 0.0 to 1.0,
  \"technical_analysis\": {
    \"algorithm_fit\": \"Does the math match the problem?\",
    \"complexity_class\": \"e.g., BQP, NP-Hard\",
    \"circuit_metrics\": {
      \"qubit_count\": \"Integer\",
      \"estimated_depth\": \"Integer\",
      \"connectivity_compliant\": \"Boolean\"
    }
  },
  \"risk_assessment\": {
    \"hallucination_detected\": \"Boolean\",
    \"physical_violation\": \"None | No-Cloning | Non-Unitary\",
    \"nisq_feasibility\": \"High | Medium | Low\"
  },
  \"citation_grounding\": [
    {
      \"claim\": \"Statement being verified\",
      \"source\": \"URL or Paper Title found via Search\"
    }
  ],
  \"architect_feedback\": \"Precise, technical instructions for remediation. Use LaTeX formatting for math.\"
}BEHAVIORAL CONSTRAINTSSkepticism: Assume the code is wrong until proven right.Precision: Never use vague phrases like \"It looks good.\" Use \"The circuit depth of 45 falls within the coherence time of the IBM Eagle processor.\"Safety: If the code contains infinite loops or excessive shot counts ($> 20,000$ without justification), flag as REJECTED for resource protection.
Implementation Guide for the DeveloperTo make this agent truly \"Enterprise,\" you need to handle the inputs and the Grounding trigger correctly.
1. The Interaction Trigger (Python/LangChain)When you send the prompt to Vertex AI, you shouldn't just send the code. You must package the reasoning requirement.
# Example Prompt Construction for Gemini 1.5 Pro
user_input = \"\"\"
AUDIT REQUEST:
1. Problem: Factor the integer 15.
2. Strategy: Shor's Algorithm.
3. Code: 
   q = QuantumRegister(2)
   c = ClassicalRegister(2)
   qc = QuantumCircuit(q, c)
   qc.h(q)
   # ... (code snippet) ...
\"\"\"

# Force the model to \"Ground\" itself first
grounding_instruction = \"\"\"
Before approving, use Google Search to verify: \"Minimum qubit requirements for Shor's algorithm to factor 15\". 
Compare the search result against the provided code's qubit count.
\"\"\"

response = model.generate_content(
    [system_prompt, user_input, grounding_instruction],
    tools=[search_tool] # Enable Vertex AI Search / Google Search
)
2. Why this is better than the original draft:Separation of Concerns: The JSON schema is strictly typed. This allows your Orchestrator (Python backend) to parse response['decision'] and automatically route the workflow (e.g., if REJECTED, send back to Architect; if APPROVED, send to Qiskit Runtime).The \"Hallucination Trap\": By explicitly asking for a Dimensionality Check and Oracle Validation, we force the model to look at the math, not just the syntax. LLMs are great at writing correct syntax for wrong logic; this prompt stops that.Resource Protection: The \"Safety\" constraint prevents the agent from approving code that burns through expensive cloud quantum credits (QPU time) unnecessarily.
3. Example of a \"REJECTED\" Response (Simulation)If the user tries to factor 15 using only 2 qubits (impossible, requires ~8+ for standard Shor's or 4-5 for compiled versions).
{
  \"audit_id\": \"audit-8821-x\",
  \"decision\": \"REJECTED\",
  \"confidence_score\": 1.0,
  \"technical_analysis\": {
    \"algorithm_fit\": \"Shor's Algorithm is correct for factoring, but implementation is flawed.\",
    \"complexity_class\": \"BQP\",
    \"circuit_metrics\": {
      \"qubit_count\": 2,
      \"estimated_depth\": 10,
      \"connectivity_compliant\": true
    }
  },
  \"risk_assessment\": {
    \"hallucination_detected\": true,
    \"physical_violation\": \"None\",
    \"nisq_feasibility\": \"High (but incorrect logic)\"
  },
  \"citation_grounding\": [
    {
      \"claim\": \"Shor's Algorithm Qubit Requirement for N=15\",
      \"source\": \"Beauregard (2002) - Circuit for Shor's algorithm requires 2n+3 qubits.\"
    }
  ],
  \"architect_feedback\": \"Scientific Error: You attempted to implement Shor's Algorithm for N=15 using only 2 qubits. Theoretical minimum for modular exponentiation requires at least 4 qubits (using Beauregard's or Pavlov's optimization). The current circuit lacks the necessary width to represent the superposition states. Revise specific to 'Variational Quantum Factoring' if limited to low qubit counts, or increase register size.\"
}""")

    def validate_proposal(self, mapping: dict, code: str) -> dict:
        user_input = f"""
AUDIT REQUEST:
1. Strategy Mapping: {json.dumps(mapping)}
2. Code: 
{code}
"""
        grounding_instruction = """
Before approving, use Google Search to verify the algorithm requirements.
Ensure the logic complies with physical rules.
"""
        contents = [
          types.Content(
            role="user",
            parts=[self.msg1_text1, types.Part.from_text(text=user_input), types.Part.from_text(text=grounding_instruction)]
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
            return {"decision": "REJECTED", "architect_feedback": "Scientist failed to output valid JSON. Output was: " + response.text}
