import pytest

@pytest.mark.asyncio
async def test_health_endpoint(async_client):
    res = await async_client.get("/health")
    assert res.status_code == 200
    assert res.json()["status"] == "healthy"

@pytest.mark.asyncio
async def test_run_research_flow(async_client):
    res = await async_client.post(
        "/api/v1/research/run",
        json={
            "topic": "Generative AI in Software Testing",
            "depth": "Detailed",
            "include_academic": True,
            "citation_style": "APA"
        }
    )
    assert res.status_code == 201
    data = res.json()
    assert "research_id" in data
    assert len(data["references"]) > 0
    assert len(data["ppt_outline"]) >= 3
    research_id = data["research_id"]

    # Test report retrieval
    get_res = await async_client.get(f"/api/v1/research/report/{research_id}")
    assert get_res.status_code == 200
    get_data = get_res.json()
    assert get_data["topic"] == "Generative AI in Software Testing"
