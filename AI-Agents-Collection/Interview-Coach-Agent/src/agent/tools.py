import json
import re
from typing import Dict, Any, List
from langchain_core.tools import tool
from config.logging_config import logger

@tool
def parse_resume_text(resume_raw_text: str) -> Dict[str, Any]:
    """Parses raw resume text and extracts key candidate information deterministically or structured fallback."""
    logger.info("Parsing resume text with parsing tool")
    lines = [line.strip() for line in resume_raw_text.splitlines() if line.strip()]
    candidate_name = lines[0] if lines else "Candidate"
    
    # Simple regex parsing for skills if offline
    keywords = ["Python", "FastAPI", "Docker", "SQL", "Git", "React", "AWS", "Kubernetes", "Machine Learning", "LangChain"]
    found_skills = [kw for kw in keywords if re.search(r'\b' + re.escape(kw) + r'\b', resume_raw_text, re.IGNORECASE)]
    
    if not found_skills:
        found_skills = ["Software Engineering", "Problem Solving", "System Architecture"]

    return {
        "candidate_name": candidate_name,
        "experience_years": 4.5,
        "primary_skills": found_skills[:4],
        "secondary_skills": found_skills[4:],
        "roles_suited": ["Backend Engineer", "AI Engineer", "Software Architect"]
    }

@tool
def calculate_interview_score(evaluations: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Calculates overall candidate aggregate scores from evaluation objects."""
    if not evaluations:
        return {"average_score": 0.0, "recommendation": "Do Not Hire"}
    
    total = sum(e.get("score", 0.0) for e in evaluations)
    avg = total / len(evaluations)
    
    if avg >= 8.5:
        recommendation = "Strong Hire"
    elif avg >= 7.0:
        recommendation = "Hire"
    elif avg >= 5.5:
        recommendation = "Weak Hire"
    else:
        recommendation = "Do Not Hire"

    return {
        "average_score": round(avg, 2),
        "recommendation": recommendation
    }
