import base64
import json
import os
import threading
import uuid
from typing import Any, Dict, List, Optional, Tuple

from google.adk.agents import LlmAgent
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types


def _configure_vertex_env() -> None:
    os.environ.setdefault("GOOGLE_GENAI_USE_VERTEXAI", "true")

    project = os.getenv("GCP_PROJECT_ID") or os.getenv("GOOGLE_CLOUD_PROJECT")
    if project:
        os.environ.setdefault("GOOGLE_CLOUD_PROJECT", project)

    location = os.getenv("GOOGLE_CLOUD_LOCATION") or os.getenv("GCP_LOCATION") or "global"
    os.environ.setdefault("GOOGLE_CLOUD_LOCATION", location)


class ADKAgentRuntime:
    def __init__(
        self,
        *,
        name: str,
        model: str,
        instruction: str,
        generate_content_config: Optional[types.GenerateContentConfig] = None,
        tools: Optional[List[Any]] = None,
        app_name: Optional[str] = None,
        user_id: str = "quantum_orchestrator",
    ) -> None:
        _configure_vertex_env()
        self.name = name
        self.user_id = user_id
        self.agent = LlmAgent(
            name=name,
            model=model,
            instruction=instruction,
            tools=tools or [],
            generate_content_config=generate_content_config,
        )
        self._session_service = InMemorySessionService()
        self._runner = Runner(
            app_name=app_name or f"{name}_app",
            agent=self.agent,
            session_service=self._session_service,
            auto_create_session=True,
        )
        self._lock = threading.Lock()

    @staticmethod
    def _extract_json_candidate(text: str) -> str:
        candidate = text.strip()
        if candidate.startswith("```"):
            lines = candidate.splitlines()
            if len(lines) >= 3:
                candidate = "\n".join(lines[1:-1]).strip()

        if candidate.startswith("{") and candidate.endswith("}"):
            return candidate
        if candidate.startswith("[") and candidate.endswith("]"):
            return candidate

        obj_start = candidate.find("{")
        obj_end = candidate.rfind("}")
        if obj_start != -1 and obj_end > obj_start:
            return candidate[obj_start : obj_end + 1]

        arr_start = candidate.find("[")
        arr_end = candidate.rfind("]")
        if arr_start != -1 and arr_end > arr_start:
            return candidate[arr_start : arr_end + 1]
        return ""

    @staticmethod
    def _collect_parts(events: List[Any]) -> Tuple[List[str], List[Dict[str, str]]]:
        text_segments: List[str] = []
        inline_assets: List[Dict[str, str]] = []

        for event in events:
            content = getattr(event, "content", None)
            parts = getattr(content, "parts", None) or []
            for part in parts:
                text = getattr(part, "text", None)
                if text and text.strip():
                    text_segments.append(text.strip())

                inline_data = getattr(part, "inline_data", None)
                if not inline_data:
                    continue

                blob = getattr(inline_data, "data", None)
                if blob is None:
                    continue

                if isinstance(blob, str):
                    encoded = blob
                else:
                    encoded = base64.b64encode(blob).decode("utf-8")

                inline_assets.append(
                    {
                        "mime_type": getattr(inline_data, "mime_type", "application/octet-stream"),
                        "data": encoded,
                    }
                )

        return text_segments, inline_assets

    def run_raw(self, prompt: str, session_id: Optional[str] = None) -> Dict[str, Any]:
        sid = session_id or str(uuid.uuid4())
        new_message = types.Content(role="user", parts=[types.Part(text=prompt)])

        try:
            with self._lock:
                events = list(
                    self._runner.run(
                        user_id=self.user_id,
                        session_id=sid,
                        new_message=new_message,
                    )
                )
        except Exception as exc:
            return {
                "session_id": sid,
                "event_count": 0,
                "text": "",
                "segments": [],
                "assets": [],
                "error": str(exc),
            }
        finally:
            try:
                self._session_service.delete_session_sync(
                    app_name=self._runner.app_name,
                    user_id=self.user_id,
                    session_id=sid,
                )
            except Exception:
                pass

        segments, assets = self._collect_parts(events)
        final_text = "\n".join(segments).strip()
        return {
            "session_id": sid,
            "event_count": len(events),
            "text": final_text,
            "segments": segments,
            "assets": assets,
        }

    def run_json(self, prompt: str, session_id: Optional[str] = None) -> Dict[str, Any]:
        raw = self.run_raw(prompt, session_id=session_id)
        if raw.get("error"):
            return {"error": raw["error"], "raw_output": raw}

        text = raw.get("text", "").strip()
        if not text:
            return {"error": "Empty response from ADK agent.", "raw_output": raw}

        parse_candidates = [text]
        parse_candidates.extend(reversed(raw.get("segments", [])))

        for candidate_text in parse_candidates:
            candidate = self._extract_json_candidate(candidate_text)
            if not candidate:
                continue
            try:
                parsed = json.loads(candidate)
                if isinstance(parsed, dict):
                    return parsed
                return {"data": parsed}
            except Exception:
                continue

        return {"error": "Failed to parse JSON from ADK response.", "raw_output": text}

    def run_interleaved(self, prompt: str, session_id: Optional[str] = None) -> Dict[str, Any]:
        raw = self.run_raw(prompt, session_id=session_id)
        if raw.get("error"):
            return {"error": raw["error"], "details": raw}

        segments = raw.get("segments", [])
        if not segments and raw.get("text"):
            segments = [raw["text"]]
        return {
            "session_id": raw.get("session_id", ""),
            "narrative_segments": segments,
            "assets": raw.get("assets", []),
        }
