from typing import Dict, Any, Optional

class InterviewMemoryStore:
    """In-memory checkpoint and state store for candidate interview sessions."""

    def __init__(self):
        self._sessions: Dict[str, Dict[str, Any]] = {}

    def save_state(self, session_id: str, state: Dict[str, Any]) -> None:
        self._sessions[session_id] = state

    def get_state(self, session_id: str) -> Optional[Dict[str, Any]]:
        return self._sessions.get(session_id)

    def delete_session(self, session_id: str) -> bool:
        if session_id in self._sessions:
            del self._sessions[session_id]
            return True
        return False

memory_store = InterviewMemoryStore()
