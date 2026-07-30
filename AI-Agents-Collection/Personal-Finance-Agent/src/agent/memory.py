from typing import Dict, Any, Optional

class FinanceMemoryStore:
    """In-memory financial session checkpointer."""

    def __init__(self):
        self._sessions: Dict[str, Dict[str, Any]] = {}

    def save_state(self, report_id: str, state: Dict[str, Any]) -> None:
        self._sessions[report_id] = state

    def get_state(self, report_id: str) -> Optional[Dict[str, Any]]:
        return self._sessions.get(report_id)

    def delete_session(self, report_id: str) -> bool:
        if report_id in self._sessions:
            del self._sessions[report_id]
            return True
        return False

memory_store = FinanceMemoryStore()
