import pytest

@pytest.mark.asyncio
async def test_health_endpoint(async_client):
    response = await async_client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"

@pytest.mark.asyncio
async def test_start_interview_flow(async_client):
    response = await async_client.post(
        "/api/v1/interview/start",
        data={
            "target_role": "Backend Developer",
            "difficulty": "Senior",
            "question_count": 3,
            "resume_text": "Sam Smith\nExperienced backend dev skilled in Go and PostgreSQL."
        }
    )
    assert response.status_code == 201
    data = response.json()
    assert "session_id" in data
    assert len(data["questions"]) > 0
    session_id = data["session_id"]

    # Test evaluate answer
    eval_resp = await async_client.post(
        "/api/v1/interview/evaluate",
        json={
            "session_id": session_id,
            "question_id": 1,
            "question_text": "Explain Go concurrency models and channels.",
            "candidate_answer": "Go uses goroutines and CSP channels to communicate between concurrent routines safely."
        }
    )
    assert eval_resp.status_code == 200
    eval_data = eval_resp.json()
    assert eval_data["score"] > 0

    # Test get report
    report_resp = await async_client.get(f"/api/v1/interview/report/{session_id}")
    assert report_resp.status_code == 200
    report_data = report_resp.json()
    assert report_data["session_id"] == session_id
    assert report_data["total_questions"] >= 1
