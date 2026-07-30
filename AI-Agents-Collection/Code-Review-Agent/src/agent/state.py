from typing import List, Dict, Any, Optional, TypedDict

class CodeReviewState(TypedDict):
    review_id: str
    filename: str
    language: str
    code_content: str
    ast_data: Optional[Dict[str, Any]]
    detected_issues: List[Dict[str, Any]]
    quality_score: float
    refactored_code: Optional[str]
    docstring_suggestion: Optional[str]
    unit_tests: Optional[str]
    status: str
    error: Optional[str]
