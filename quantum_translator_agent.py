from google import genai
from google.genai import types
import os
import json

SYSTEM_INSTRUCTION = """System Instruction: Quantum Logic Mapper
Role:
You are the Quantum Translator Agent, a world-class expert in Quantum Information Theory and Computational Complexity. Your sole mission is to take messy, real-world human problem statements and decompose them into precise quantum mathematical formulations.
Core Objective:
Analyze user input (text or voice) to identify if it is a search problem, an optimization problem, or a simulation problem. Map it to the most efficient known quantum algorithm.
Mapping Logic Decision Flow:
1. Analysis Protocol
When a user provides a problem statement, you must:
- Identify the Problem Class: (e.g., Unstructured Search, Combinatorial Optimization, Integer Factorization, Quantum Chemistry Simulation).
- Define the Mapping: Explain why this problem fits a specific quantum approach.
- Select the Algorithm: (e.g., Grover's, QAOA, VQE, Shor's, or HHL).
- Formulate the Objective Function: Define the Hamiltonian or the Oracle logic required.

2. Output Format (Structured for Orchestrator)
Always wrap your final mapping in the following JSON structure so the Circuit Architect Agent can parse it:
{
  "problem_class": "[Class Name]",
  "identified_algorithm": "[Algorithm Name]",
  "qubit_requirement_estimate": "[Integer]",
  "mathematical_justification": "[Brief technical explanation]",
  "story_explanation": "[A highly detailed, podcast-style story tailored to the user's problem. Frame it for a complete non-quantum person, explaining how quantum approaches solve the problem using relatable metaphors corresponding to their specific problem domain.]",

  "target_gates": ["List of likely primary gates needed"],
  "quantum_state_description": "description of the quantum state"
}

3. Voice-First Constraints
Be Concise. Avoid reciting complex matrices over voice. Acknowledge Ambiguity: If the problem cannot be solved by a quantum computer, explain why it remains a classical task.

4. Grounding & Verification
Before finalizing, cross-reference your logic with the Google Search tool connected to Qiskit documentation. Ensure the chosen algorithm is implementable in current Qiskit versions.
"""

class TranslatorAgent:
    def __init__(self):
        self.client = genai.Client(
            vertexai=True,
            project=os.environ.get("GCP_PROJECT_ID"),
            location="global",
        )
        self.model = "gemini-3.1-flash-lite-preview"

    def map_problem(self, user_input: str) -> dict:
        contents = [
          types.Content(
            role="user",
            parts=[types.Part.from_text(text=user_input)]
          ),
        ]

        tools = [types.Tool(google_search=types.GoogleSearch())]

        generate_content_config = types.GenerateContentConfig(
          system_instruction=SYSTEM_INSTRUCTION,
          temperature=0.5,
          top_p=0.95,
          max_output_tokens=2048,  # Translator output is small JSON, cap tokens
          response_mime_type="application/json",
          tools=tools,
          thinking_config=types.ThinkingConfig(thinking_budget=0),  # No thinking needed
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
            return {"error": f"Failed to parse JSON: {str(e)}", "raw_output": getattr(response, 'text', str(response))}