from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from datetime import datetime

class CodeReviewRequest(BaseModel):
    repository_url: Optional[str] = Field(None, description="GitHub repository URL")
    code_filename: Optional[str] = Field("main.py", description="Target filename")
    code_content: Optional[str] = Field(None, description="Raw source code string")
    language: str = Field(default="python", description="python, javascript, typescript, go, etc.")

class IssueItem(BaseModel):
    issue_type: str = Field(description="Bug, Security, Performance, CodeSmell, Duplicate")
    severity: str = Field(description="Critical, High, Medium, Low")
    line_number: Optional[int] = None
    title: str
    description: str
    suggested_fix: str

class CodeReviewReportResponse(BaseModel):
    review_id: str
    filename: str
    language: str
    total_issues: int
    quality_score: float = Field(description="Code Quality Score out of 100")
    bugs_count: int
    security_vulnerabilities_count: int
    code_smells_count: int
    performance_issues_count: int
    issues: List[IssueItem]
    docstring_suggestion: Optional[str] = None
    refactored_code: Optional[str] = None
    generated_unit_tests: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
