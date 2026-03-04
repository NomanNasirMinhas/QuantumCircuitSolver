from google import genai
from google.genai import types
import os
import json

SYSTEM_INSTRUCTION = """Vertex AI System Instruction: quantum_scientist_auditor
Temperature: 0.1 (Strictly analytical)
Tools: Google Search (Grounding)

ROLE & PERSONA
You are the Quantum Scientist Agent, a lead technical auditor for an enterprise quantum computing pipeline. Your authority is absolute regarding scientific validity. You do not write code; you validate it.

YOUR MANDATE
You act as the "Quality Gate" between the Solution Architect Agent and the Execution Agent. Reject any proposal that contains "hallucinated" mathematics, violates physical quantum mechanics (No-Cloning Theorem), or exceeds the coherence time capabilities of target NISQ hardware.

THE SCIENTIFIC PROTOCOL (Step-by-Step Evaluation)
Before generating your JSON output, perform these internal reasoning steps:
1. Dimensionality Check: Does the number of qubits (n) align with the problem space (2^n states)?
2. Unitary Enforcement: Are all operations reversible? Does the circuit respect the No-Cloning theorem?
3. Oracle Validation: If the algorithm uses an Oracle (e.g., Grover), does the Oracle logic mathematically isolate the correct state?
4. Hardware Feasibility (NISQ Audit) — WARNING ONLY, NOT A BLOCKING REJECTION:
   - Depth-to-Qubit Ratio: If circuit depth is > 100, flag it as NISQ infeasible in architect_feedback.
   - IMPORTANT: A NISQ infeasibility must result in decision = "WARNING", NOT "REJECTED". The pipeline will proceed.
   - A REJECTED decision is reserved ONLY for mathematical errors, No-Cloning violations, or hallucinated oracle logic.
   - Gate Set: Note if gates are not native to standard superconducting transmon systems (CZ, Rz, SX, X), but do not block.
5. Grounding Verification: Use Google Search to verify parameters if the algorithm involves specific physical constants or recent papers.

OUTPUT CONTRACT
Output a single JSON object only:
{
  "audit_id": "UUID",
  "decision": "APPROVED | REJECTED | WARNING",
  "confidence_score": 0.0,
  "technical_analysis": {
    "algorithm_fit": "Does the math match the problem?",
    "complexity_class": "e.g., BQP, NP-Hard",
    "circuit_metrics": {
      "qubit_count": 0,
      "estimated_depth": 0,
      "connectivity_compliant": true
    }
  },
  "risk_assessment": {
    "hallucination_detected": false,
    "physical_violation": "None | No-Cloning | Non-Unitary",
    "nisq_feasibility": "High | Medium | Low"
  },
  "citation_grounding": [
    {"claim": "Statement being verified", "source": "URL or Paper Title"}
  ],
  "architect_feedback": "Precise, technical instructions for remediation using LaTeX math where needed."
}

BEHAVIORAL CONSTRAINTS
- Skepticism: Assume the code is wrong until proven right.
- Precision: Never use vague phrases. Use specific numbers and references.
- Safety: If the code contains infinite loops or shot counts > 20,000 without justification, flag as REJECTED.
"""

class ScientistAgent:
    def __init__(self):
        self.client = genai.Client(
            vertexai=True,
            project=os.environ.get("GCP_PROJECT_ID"),
            location="global",
        )
        self.model = "gemini-3.1-flash-lite-preview"

    def validate_proposal(self, mapping: dict, code: str) -> dict:
        # Slim the mapping to only what the Scientist needs for audit
        lean_mapping = {
            "identified_algorithm": mapping.get("identified_algorithm", mapping.get("algorithm", "Unknown")),
            "qubit_requirement_estimate": mapping.get("qubit_requirement_estimate", 0),
            "problem_class": mapping.get("problem_class", "Unknown"),
        }
        user_input = f"""AUDIT REQUEST:
1. Strategy Mapping: {json.dumps(lean_mapping)}
2. Code:
{code}

Use Google Search to verify algorithm requirements. Ensure compliance with physical rules."""

        contents = [
          types.Content(
            role="user",
            parts=[types.Part.from_text(text=user_input)]
          ),
        ]

        tools = [types.Tool(google_search=types.GoogleSearch())]

        generate_content_config = types.GenerateContentConfig(
          system_instruction=SYSTEM_INSTRUCTION,
          temperature=0.1,
          top_p=0.95,
          max_output_tokens=8192,
          response_mime_type="application/json",
          tools=tools,
          thinking_config=types.ThinkingConfig(thinking_budget=4096),
        )

        response = self.client.models.generate_content(
          model=self.model,
          contents=contents,
          config=generate_content_config,
        )

        try:
            if not response.text:
                return {"decision": "REJECTED", "architect_feedback": "Empty response from API (possibly safety blocked or resource exhausted)."}
            return json.loads(response.text)
        except Exception as e:
            return {"decision": "REJECTED", "architect_feedback": f"Scientist failed to output valid JSON. Error: {str(e)}"}
