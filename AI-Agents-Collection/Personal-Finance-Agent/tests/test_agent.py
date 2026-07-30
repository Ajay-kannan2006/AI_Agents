import pytest
from src.agent.tools import parse_statement_csv, calculate_financial_health_score, generate_pie_chart_svg
from src.agent.graph import finance_graph

def test_parse_csv_tool():
    csv_str = "date,description,amount\n2026-07-01,Rent,1500.00\n2026-07-02,Groceries,120.00"
    txs = parse_statement_csv.invoke({"csv_content": csv_str})
    assert len(txs) == 2
    assert txs[0]["description"] == "Rent"

def test_health_score_tool():
    res = calculate_financial_health_score.invoke({"income": 6000.0, "expenses": 3000.0, "savings_goal": 1500.0})
    assert res["score"] >= 75.0
    assert res["savings_rate_percent"] == 50.0

def test_chart_svg_tool():
    cats = {"Housing": 1500.0, "Groceries": 400.0}
    svg = generate_pie_chart_svg.invoke({"categories": cats})
    assert "<svg" in svg
    assert "Housing" in svg

def test_finance_graph_pipeline():
    initial_state = {
        "report_id": "test-fin-123",
        "monthly_income": 5000.0,
        "savings_goal": 1000.0,
        "raw_csv": "date,description,amount\n2026-07-01,Rent,2000.00\n2026-07-05,Netflix,15.99",
        "transactions": [],
        "categories": {},
        "recurring_expenses": [],
        "health_score": 0.0,
        "forecast_amount": 0.0,
        "suggestions": [],
        "investments": [],
        "chart_svg": None,
        "status": "init",
        "error": None
    }
    out = finance_graph.invoke(initial_state)
    assert out["status"] == "completed"
    assert out["health_score"] > 0
    assert "Housing" in out["categories"]
