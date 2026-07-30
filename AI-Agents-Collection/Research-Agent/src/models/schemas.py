from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from datetime import datetime

class ResearchRequest(BaseModel):
    topic: str = Field(..., description="Target research topic or academic question")
    depth: str = Field(default="Detailed", description="Brief, Detailed, or Comprehensive")
    include_academic: bool = Field(default=True, description="Whether to search academic papers")
    citation_style: str = Field(default="APA", description="APA, MLA, or BibTeX")

class SearchResultItem(BaseModel):
    title: str
    url: str
    snippet: str
    source_type: str = Field(description="Web or Academic")
    author: Optional[str] = None
    year: Optional[int] = None

class PresentationSlide(BaseModel):
    slide_number: int
    slide_title: str
    bullet_points: List[str]

class ResearchReportResponse(BaseModel):
    research_id: str
    topic: str
    executive_summary: str
    keywords: List[str]
    key_findings: List[str]
    full_report_markdown: str
    references: List[str]
    ppt_outline: List[PresentationSlide]
    topic_comparison_matrix: Optional[Dict[str, Any]] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
