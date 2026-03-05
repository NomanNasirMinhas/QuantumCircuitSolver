import os

from google.adk.agents import LlmAgent, SequentialAgent
from google.adk.tools import google_search
from google.genai import types


def _configure_vertex_env() -> None:
    os.environ.setdefault("GOOGLE_GENAI_USE_VERTEXAI", "true")
    project = os.getenv("GCP_PROJECT_ID") or os.getenv("GOOGLE_CLOUD_PROJECT")
    if project:
        os.environ.setdefault("GOOGLE_CLOUD_PROJECT", project)
    os.environ.setdefault("GOOGLE_CLOUD_LOCATION", os.getenv("GOOGLE_CLOUD_LOCATION", "global"))


def _json_config(*, temperature: float, max_output_tokens: int, thinking_budget: int = 0) -> types.GenerateContentConfig:
    kwargs = {
        "temperature": temperature,
        "top_p": 0.95,
        "max_output_tokens": max_output_tokens,
        "response_mime_type": "application/json",
    }
    if thinking_budget > 0:
        kwargs["thinking_config"] = types.ThinkingConfig(thinking_budget=thinking_budget)
    return types.GenerateContentConfig(**kwargs)


_configure_vertex_env()


translator_agent = LlmAgent(
    name="translator",
    model=os.getenv("TRANSLATOR_MODEL", "gemini-3.1-flash-lite-preview"),
    description="Maps user problem statements into quantum algorithm candidates.",
    instruction=(
        "You are the Quantum Translator Agent. Classify the user problem and map it to the most suitable "
        "quantum algorithm. Return JSON with: problem_class, identified_algorithm, qubit_requirement_estimate, "
        "mathematical_justification, story_explanation, target_gates, quantum_state_description."
    ),
    tools=[google_search],
    generate_content_config=_json_config(temperature=0.5, max_output_tokens=8192),
    output_key="mapping",
)

architect_agent = LlmAgent(
    name="architect",
    model=os.getenv("ARCHITECT_MODEL", "gemini-3.1-pro-preview"),
    description="Generates executable Qiskit code from the mapped algorithm.",
    instruction=(
        "You are the Quantum Circuit Architect Agent. Use conversation context (especially translator output) "
        "to produce optimized Qiskit Python code. Return JSON with: python_code, explanation. Ensure code uses "
        "AerSimulator, transpile(..., optimization_level=3), prints measurement counts, and writes circuit.png."
    ),
    tools=[google_search],
    generate_content_config=_json_config(temperature=0.2, max_output_tokens=8192, thinking_budget=2048),
    output_key="code_package",
)

scientist_agent = LlmAgent(
    name="scientist",
    model=os.getenv("SCIENTIST_MODEL", "gemini-3.1-flash-lite-preview"),
    description="Audits scientific validity and hardware feasibility.",
    instruction=(
        "You are the Quantum Scientist Auditor. Validate mathematical correctness and physical consistency. "
        "Return JSON with: audit_id, decision (APPROVED|REJECTED|WARNING), confidence_score, technical_analysis, "
        "risk_assessment, citation_grounding, architect_feedback."
    ),
    tools=[google_search],
    generate_content_config=_json_config(temperature=0.1, max_output_tokens=8192, thinking_budget=4096),
    output_key="scientific_report",
)

evaluator_agent = LlmAgent(
    name="evaluator",
    model=os.getenv("EVALUATOR_MODEL", "gemini-3.1-flash-lite-preview"),
    description="Performs final quality verdict on the proposed solution.",
    instruction=(
        "You are the Quantum Evaluator Agent. Validate logical alignment, scientific accuracy, and pedagogical "
        "clarity using prior context from translator/architect/scientist. Return JSON with: verdict (PASS|FAIL), "
        "confidence_score, validation_summary, error_analysis, feedback_for_agents."
    ),
    generate_content_config=_json_config(temperature=0.1, max_output_tokens=8192, thinking_budget=2048),
    output_key="evaluator_report",
)

media_producer_agent = LlmAgent(
    name="media_producer",
    model=os.getenv("MEDIA_STRUCTURED_MODEL", "gemini-3.1-flash-lite-preview"),
    description="Creates multimodal storytelling prompts and narrative script.",
    instruction=(
        "You are the Quantum Media Producer Agent. Use prior context to create a compelling media brief. "
        "Return JSON with: asset_type, concept_focus, veo_video_prompt, imagen_graphic_prompt, audio_script."
    ),
    tools=[google_search],
    generate_content_config=_json_config(temperature=0.7, max_output_tokens=8192),
    output_key="media_brief",
)

root_agent = SequentialAgent(
    name="quantum_circuit_orchestrator",
    description="Multi-agent quantum workflow built with Google ADK.",
    sub_agents=[
        translator_agent,
        architect_agent,
        scientist_agent,
        evaluator_agent,
        media_producer_agent,
    ],
)
