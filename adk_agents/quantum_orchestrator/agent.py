import os
from typing import Any, Dict, Optional

from google.adk.agents import LlmAgent, SequentialAgent
from google.adk.tools import google_search
from google.genai import types

from circuit_architect_agent import SYSTEM_INSTRUCTION as ARCHITECT_SYSTEM_INSTRUCTION
from evaluator_agent import SYSTEM_INSTRUCTION as EVALUATOR_SYSTEM_INSTRUCTION
from media_generator_agent import MediaProducerAgent
from media_generator_agent import STORYBOOK_SYSTEM_INSTRUCTION as MEDIA_STORYBOOK_SYSTEM_INSTRUCTION
from quantum_scientist_agent import SYSTEM_INSTRUCTION as SCIENTIST_SYSTEM_INSTRUCTION
from quantum_translator_agent import SYSTEM_INSTRUCTION as TRANSLATOR_SYSTEM_INSTRUCTION


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
_media_runtime: Optional[MediaProducerAgent] = None


def _get_media_runtime() -> MediaProducerAgent:
    global _media_runtime
    if _media_runtime is None:
        _media_runtime = MediaProducerAgent()
    return _media_runtime


def generate_storybook(mapping: Dict[str, Any], code: str, page_count: int = 8) -> Dict[str, Any]:
    """Generate a full storyline with per-page illustration and per-page audio."""
    return _get_media_runtime().generate_storybook(
        mapping=mapping,
        code=code,
        page_count=page_count,
        include_page_images=True,
        include_page_audio=True,
    )


translator_agent = LlmAgent(
    name="translator",
    model=os.getenv("TRANSLATOR_MODEL", "gemini-3.1-flash-lite-preview"),
    description="Maps user problem statements into quantum algorithm candidates.",
    instruction=TRANSLATOR_SYSTEM_INSTRUCTION,
    tools=[google_search],
    generate_content_config=_json_config(temperature=0.5, max_output_tokens=8192),
    output_key="mapping",
)

architect_agent = LlmAgent(
    name="architect",
    model=os.getenv("ARCHITECT_MODEL", "gemini-3.1-pro-preview"),
    description="Generates executable Qiskit code from the mapped algorithm.",
    instruction=ARCHITECT_SYSTEM_INSTRUCTION,
    tools=[google_search],
    generate_content_config=_json_config(temperature=0.2, max_output_tokens=8192, thinking_budget=2048),
    output_key="code_package",
)

scientist_agent = LlmAgent(
    name="scientist",
    model=os.getenv("SCIENTIST_MODEL", "gemini-3.1-pro-preview"),
    description="Audits scientific validity and hardware feasibility.",
    instruction=SCIENTIST_SYSTEM_INSTRUCTION,
    tools=[google_search],
    generate_content_config=_json_config(temperature=0.1, max_output_tokens=8192, thinking_budget=4096),
    output_key="scientific_report",
)

evaluator_agent = LlmAgent(
    name="evaluator",
    model=os.getenv("EVALUATOR_MODEL", "gemini-3.1-pro-preview"),
    description="Performs final quality verdict on the proposed solution.",
    instruction=EVALUATOR_SYSTEM_INSTRUCTION,
    generate_content_config=_json_config(temperature=0.1, max_output_tokens=8192, thinking_budget=2048),
    output_key="evaluator_report",
)

media_producer_storybook_agent = LlmAgent(
    name="media_producer_storybook",
    model=os.getenv("MEDIA_STORYBOOK_MODEL", "gemini-3.1-flash-lite-preview"),
    description="Creates page-based storyline output with per-page narration and illustrations.",
    instruction=MEDIA_STORYBOOK_SYSTEM_INSTRUCTION,
    tools=[google_search, generate_storybook],
    generate_content_config=_json_config(temperature=0.7, max_output_tokens=8192),
    output_key="storybook_package",
)

root_agent = SequentialAgent(
    name="quantum_circuit_orchestrator",
    description="Multi-agent quantum workflow built with Google ADK.",
    sub_agents=[
        translator_agent,
        architect_agent,
        scientist_agent,
        evaluator_agent,
        media_producer_storybook_agent,
    ],
)
