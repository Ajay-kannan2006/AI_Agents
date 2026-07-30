import pytest

@pytest.mark.asyncio
async def test_health_endpoint(async_client):
    res = await async_client.get("/health")
    assert res.status_code == 200
    assert res.json()["status"] == "healthy"

@pytest.mark.asyncio
async def test_finance_analyze_endpoint(async_client):
    res = await async_client.post(
        "/api/v1/finance/analyze",
        data={
            "monthly_income": 6000.0,
            "savings_goal": 1500.0,
            "statement_csv_text": "date,description,amount\n2026-07-01,Apartment Rent,2000.00\n2026-07-05,Trader Joes,150.00"
        }
    )
    assert res.status_code == 201
    data = res.json()
    assert "report_id" in data
    assert data["financial_health_score"] > 0
    assert len(data["category_breakdown"]) > 0
    assert data["chart_svg"] is not None
