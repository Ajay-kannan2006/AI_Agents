from typing import Dict, Any, Optional

class CodeReviewMemoryStore:
    """In-memory code review task state checkpointer."""

    def __init__(self):
        self._sessions: Dict[str, Dict[str, Any]] = {}

    def save_state(self, review_id: str, state: Dict[str, Any]) -> None:
        self._sessions[review_id] = state

    def get_state(self, review_id: str) -> Optional[Dict[str, Any]]:
        return self._sessions.get(review_id)

    def delete_session(self, review_id: str) -> bool:
        if review_id in self._sessions:
            del self._sessions[review_id]
            return True
        return False

memory_store = CodeReviewMemoryStore()
