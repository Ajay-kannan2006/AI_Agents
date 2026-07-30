from typing import List, Dict, Any, Optional, TypedDict

class InterviewState(TypedDict):
    session_id: str
    resume_text: str
    target_role: str
    difficulty: str
    extracted_skills: Optional[Dict[str, Any]]
    questions: List[Dict[str, Any]]
    current_question_index: int
    candidate_answers: List[Dict[str, Any]]
    evaluations: List[Dict[str, Any]]
    overall_summary: Optional[Dict[str, Any]]
    status: str
    error: Optional[str]
