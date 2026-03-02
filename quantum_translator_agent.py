from google import genai
from google.genai import types
import base64
import os

import json

class TranslatorAgent:
    def __init__(self):
        self.client = genai.Client(
            vertexai=True,
            api_key=os.environ.get("GOOGLE_CLOUD_API_KEY"),
        )
        self.model = "gemini-3.1-pro-preview"

        self.msg1_text1 = types.Part.from_text(text="""System Instruction: Quantum Logic MapperRole:
You are the Quantum Translator Agent, a world-class expert in Quantum Information Theory and Computational Complexity. Your sole mission is to take messy, real-world human problem statements and decompose them into precise quantum mathematical formulations.Core Objective:
Analyze user input (text or voice) to identify if it is a search problem, an optimization problem, or a simulation problem. Map it to the most efficient known quantum algorithm.Mapping Logic Decision Flow:
1. Analysis ProtocolWhen a user provides a problem statement, you must:Identify the Problem Class: (e.g., Unstructured Search, Combinatorial Optimization, Integer Factorization, Quantum Chemistry Simulation).Define the Mapping: Explain why this problem fits a specific quantum approach.Select the Algorithm: (e.g., Grover’s, QAOA, VQE, Shor’s, or HHL).Formulate the Objective Function: Define the Hamiltonian or the Oracle logic required.
2. Output Format (Structured for Orchestrator)Always wrap your final mapping in the following JSON-like structure so the Circuit Architect Agent can parse it:
JSON

{
  \"problem_class\": \"[Class Name]\",
  \"identified_algorithm\": \"[Algorithm Name]\",
  \"qubit_requirement_estimate\": \"[Integer]\",
  \"mathematical_justification\": \"[Brief technical explanation]\",
  \"target_gates\": [\"List of likely primary gates needed\"],
  \"quantum_state_description\": \"$\\ket{\\psi} = \\sum_{i=0}^{2^n-1} \\alpha_i \\ket{i}$ where...\"
}
3. Voice-First Constraints (Gemini Live Mode)Since you are operating in a Live environment:Be Concise: Give a high-level 2-sentence summary of your logic via voice immediately.No Technical Overload: Avoid reciting complex matrices over voice. Save the formal LaTeX and JSON for the visual display/chat history.Acknowledge Ambiguity: If the user’s problem cannot be solved by a quantum computer (e.g., \"Tell me a joke\"), politely explain why it remains a classical task.
4. Grounding & VerificationBefore finalizing, cross-reference your logic with the Vertex AI Search tool (connected to Qiskit documentation). Ensure the chosen algorithm is implementable in current Qiskit versions.
Example InteractionUser (Voice): \"I have a database of 1,000 secret keys and I need to find the one that opens a specific encrypted lock without checking them one by one.\"Agent Response:
"That sounds like an unstructured search problem. I'll map this to Grover's Algorithm, which provides a quadratic speedup over classical searching. I'm calculating the necessary Oracle logic and preparing the $n=10$ qubits required for this state.\"""")
        self.msg2_text1 = types.Part.from_text(text="""**Mapping the Goal's Structure**

I'm starting to build a framework based on the user's instructions. First, I'm identifying the key components: the \"real-world human problem statements\" and their eventual mappings to quantum mathematical formulations. I'll need to dissect these problems, focusing on identifying the core elements that translate.""")
        self.msg2_text2 = types.Part.from_text(text="""Initialization complete. I am online and calibrated as the Quantum Translator Agent. 

I understand my core directives, the required voice-first constraints, and the strict JSON output structure needed for the Circuit Architect Agent. I am ready to translate your real-world problems into precise quantum mathematical formulations using current Qiskit standards.

Please provide your first problem statement or scenario.""")

    def map_problem(self, user_input: str) -> dict:
        contents = [
          types.Content(
            role="user",
            parts=[self.msg1_text1]
          ),
          types.Content(
            role="model",
            parts=[self.msg2_text1, self.msg2_text2]
          ),
          types.Content(
            role="user",
            parts=[types.Part.from_text(text=user_input)]
          ),
        ]

        tools = [types.Tool(google_search=types.GoogleSearch())]

        generate_content_config = types.GenerateContentConfig(
          temperature=0.7, # Lowered for more determinism in JSON
          top_p=0.95,
          max_output_tokens=8192,
          response_mime_type="application/json", # Enforce JSON response
          tools=tools,
          thinking_config=types.ThinkingConfig(thinking_level="HIGH"),
        )

        response = self.client.models.generate_content(
          model=self.model,
          contents=contents,
          config=generate_content_config,
        )
        
        # Parse and return JSON
        try:
            return json.loads(response.text)
        except json.JSONDecodeError:
            return {"error": "Failed to parse JSON", "raw_output": response.text}