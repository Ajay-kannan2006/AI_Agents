import pytest
from src.agent.tools import parse_python_ast, detect_hardcoded_secrets, calculate_code_quality_index
from src.agent.graph import code_review_graph

def test_parse_python_ast_tool():
    code = "def hello():\n    return 'world'"
    res = parse_python_ast.invoke({"code_string": code})
    assert res["ast_valid"] is True
    assert "hello" in res["functions"]

def test_detect_secrets_tool():
    code = "API_KEY = 'AKIAIOSFODNN7EXAMPLE_SECRET_KEY'"
    issues = detect_hardcoded_secrets.invoke({"code_string": code})
    assert len(issues) >= 1
    assert issues[0]["issue_type"] == "Security"

def test_code_review_graph_pipeline():
    initial_state = {
        "review_id": "test-code-123",
        "filename": "test.py",
        "language": "python",
        "code_content": "def add(a, b):\n    return a + b",
        "ast_data": None,
        "detected_issues": [],
        "quality_score": 100.0,
        "refactored_code": None,
        "docstring_suggestion": None,
        "unit_tests": None,
        "status": "init",
        "error": None
    }
    out = code_review_graph.invoke(initial_state)
    assert out["status"] == "completed"
    assert out["refactored_code"] is not None
    assert out["generated_unit_tests"] is not None
