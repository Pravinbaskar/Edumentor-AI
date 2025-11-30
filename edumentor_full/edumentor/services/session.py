from __future__ import annotations

from typing import Dict, Any
import uuid


class SessionService:
    """In-memory session store for demo.

    In production this could be backed by Redis or a database.
    """

    def __init__(self) -> None:
        self._sessions: Dict[str, Dict[str, Any]] = {}

    def create_session(self, user_id: str) -> str:
        session_id = str(uuid.uuid4())
        self._sessions[session_id] = {
            "user_id": user_id,
            "messages": [],
            "history_summary": "",
            "current_topic": None,
        }
        return session_id

    def get_session(self, session_id: str) -> Dict[str, Any]:
        return self._sessions.setdefault(
            session_id,
            {
                "user_id": None,
                "messages": [],
                "history_summary": "",
                "current_topic": None,
            },
        )

    def add_message(self, session_id: str, role: str, content: str) -> None:
        session = self.get_session(session_id)
        session["messages"].append({"role": role, "content": content})
        # Keep only last 10 raw messages; older ones should be summarised
        session["messages"] = session["messages"][-10:]
