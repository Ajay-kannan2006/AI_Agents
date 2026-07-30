from typing import Dict, Any, Optional

class ResearchMemoryStore:
    """In-memory topic research state checkpointer."""

    def __init__(self):
        self._sessions: Dict[str, Dict[str, Any]] = {}

    def save_state(self, research_id: str, state: Dict[str, Any]) -> None:
        self._sessions[research_id] = state

    def get_state(self, research_id: str) -> Optional[Dict[str, Any]]:
        return self._sessions.get(research_id)

    def delete_session(self, research_id: str) -> bool:
        if research_id in self._sessions:
            del self._sessions[research_id]
            return True
        return False

memory_store = ResearchMemoryStore()
