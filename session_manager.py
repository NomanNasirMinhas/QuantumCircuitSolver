import json
import uuid
import os
from datetime import datetime, timezone
from typing import Dict, Any, Optional, List

SESSIONS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "sessions")


class SessionManager:
    """Manages workflow checkpoint persistence for resume-after-interruption."""

    def __init__(self):
        os.makedirs(SESSIONS_DIR, exist_ok=True)

    def _session_path(self, session_id: str) -> str:
        return os.path.join(SESSIONS_DIR, f"{session_id}.json")

    def create_session(self, user_input: str) -> str:
        """Create a new session and return its ID."""
        session_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc).isoformat()
        session = {
            "session_id": session_id,
            "user_input": user_input,
            "stage": "CREATED",
            "attempt": 0,
            "created_at": now,
            "updated_at": now,
            "data": {
                "mapping": None,
                "code_package": None,
                "scientific_report": None,
                "evaluator_report": None,
                "nisq_warning": None,
            },
        }
        with open(self._session_path(session_id), "w", encoding="utf-8") as f:
            json.dump(session, f, indent=2, ensure_ascii=False)
        return session_id

    def checkpoint(
        self, session_id: str, stage: str, data_updates: Dict[str, Any], attempt: int = 0
    ) -> None:
        """Update a session's stage and merge new data."""
        session = self.load_session(session_id)
        if session is None:
            raise ValueError(f"Session {session_id} not found")

        session["stage"] = stage
        session["attempt"] = attempt
        session["updated_at"] = datetime.now(timezone.utc).isoformat()
        session["data"].update(data_updates)

        with open(self._session_path(session_id), "w", encoding="utf-8") as f:
            json.dump(session, f, indent=2, ensure_ascii=False)

    def load_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Load a session by ID. Returns None if not found."""
        path = self._session_path(session_id)
        if not os.path.exists(path):
            return None
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)

    def list_sessions(self) -> List[Dict[str, Any]]:
        """Return summary metadata for all saved sessions."""
        sessions = []
        if not os.path.exists(SESSIONS_DIR):
            return sessions
        for filename in os.listdir(SESSIONS_DIR):
            if not filename.endswith(".json"):
                continue
            try:
                with open(os.path.join(SESSIONS_DIR, filename), "r", encoding="utf-8") as f:
                    s = json.load(f)
                sessions.append({
                    "session_id": s["session_id"],
                    "user_input": s["user_input"],
                    "stage": s["stage"],
                    "attempt": s.get("attempt", 0),
                    "created_at": s["created_at"],
                    "updated_at": s["updated_at"],
                })
            except (json.JSONDecodeError, KeyError):
                continue
        # Most recent first
        sessions.sort(key=lambda x: x["updated_at"], reverse=True)
        return sessions

    def delete_session(self, session_id: str) -> bool:
        """Delete a session file. Returns True if deleted."""
        path = self._session_path(session_id)
        if os.path.exists(path):
            os.remove(path)
            return True
        return False
