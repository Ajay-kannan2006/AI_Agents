import pytest

@pytest.mark.asyncio
async def test_health_endpoint(async_client):
    res = await async_client.get("/health")
    assert res.status_code == 200
    assert res.json()["status"] == "healthy"

@pytest.mark.asyncio
async def test_code_review_analyze_endpoint(async_client):
    res = await async_client.post(
        "/api/v1/code-review/analyze",
        data={
            "code_filename": "app.py",
            "language": "python",
            "code_content": "def calculate(val):\n    SECRET = '12345'\n    return val * 2"
        }
    )
    assert res.status_code == 201
    data = res.json()
    assert "review_id" in data
    assert data["total_issues"] >= 1
    assert data["generated_unit_tests"] is not None
