from typing import List, Dict, Any, Optional, TypedDict

class ResearchState(TypedDict):
    research_id: str
    topic: str
    depth: str
    include_academic: bool
    citation_style: str
    search_results: List[Dict[str, Any]]
    document_summaries: List[str]
    keywords: List[str]
    report_markdown: str
    references: List[str]
    ppt_outline: List[Dict[str, Any]]
    topic_matrix: Optional[Dict[str, Any]]
    status: str
    error: Optional[str]
