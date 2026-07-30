import pytest
from src.agent.tools import parse_resume_text, calculate_interview_score
from src.agent.graph import interview_graph

def test_parse_resume_tool():
    sample_text = "Jane Doe\nPython Developer with Docker experience."
    res = parse_resume_text.invoke(sample_text)
    assert res["candidate_name"] == "Jane Doe"
    assert "Python" in res["primary_skills"] or "Docker" in res["primary_skills"]

def test_calculate_interview_score_tool():
    evals = [
        {"score": 9.0},
        {"score": 8.0},
        {"score": 7.0}
    ]
    res = calculate_interview_score.invoke({"evaluations": evals})
    assert res["average_score"] == 8.0
    assert res["recommendation"] == "Hire"

def test_interview_graph_execution():
    initial_state = {
        "session_id": "test-session-123",
        "resume_text": "Alex Dev\nFullstack Engineer expert in FastAPI and React",
        "target_role": "Fullstack Engineer",
        "difficulty": "Intermediate",
        "extracted_skills": None,
        "questions": [],
        "current_question_index": 0,
        "candidate_answers": [],
        "evaluations": [],
        "overall_summary": None,
        "status": "init",
        "error": None
    }
    out = interview_graph.invoke(initial_state)
    assert out["status"] == "questions_generated"
    assert len(out["questions"]) > 0
    assert out["extracted_skills"]["candidate_name"] == "Alex Dev"
