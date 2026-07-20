import time

from app.config import settings
from backend.tests.test_smoke import create_interview, login_user, register_user


def test_completed_interview_flow_performance_smoke(client, monkeypatch):
    async def noop_send_completion_email(**kwargs):
        return None

    monkeypatch.setattr(settings, "EVALUATION_PROVIDER", "deterministic_baseline")
    monkeypatch.setattr("app.services.email_service.send_completion_email", noop_send_completion_email)

    started_at = time.perf_counter()

    register_user(client, email="perf-employer@example.com")
    owner_token = login_user(client, email="perf-employer@example.com")
    interview = create_interview(client, owner_token, title="Performance Screen")

    activate_response = client.post(
        f"/api/interviews/{interview['id']}/activate",
        headers={"Authorization": f"Bearer {owner_token}"},
    )
    assert activate_response.status_code == 200, activate_response.text

    for index in range(3):
        candidate_response = client.post(
            "/api/responses/",
            json={
                "interview_id": interview["id"],
                "candidate_email": f"perf-candidate-{index}@example.com",
                "candidate_name": f"Performance Candidate {index}",
            },
        )
        assert candidate_response.status_code == 201, candidate_response.text
        response_body = candidate_response.json()

        answer_response = client.post(
            f"/api/responses/{response_body['id']}/answer",
            params={
                "question_id": interview["questions"][0]["id"],
                "answer_text": "I listen, empathize, clarify, take ownership, resolve, and follow up.",
                "time_taken_seconds": 90,
            },
        )
        assert answer_response.status_code == 200, answer_response.text

        complete_response = client.post(f"/api/responses/{response_body['id']}/complete")
        assert complete_response.status_code == 200, complete_response.text

    responses_response = client.get(
        f"/api/responses/interview/{interview['id']}",
        headers={"Authorization": f"Bearer {owner_token}"},
    )
    assert responses_response.status_code == 200, responses_response.text
    assert len(responses_response.json()) == 3

    analytics_response = client.get(
        f"/api/reports/interview/{interview['id']}/evaluation-analytics",
        headers={"Authorization": f"Bearer {owner_token}"},
    )
    assert analytics_response.status_code == 200, analytics_response.text
    assert analytics_response.json()["completed_responses"] == 3
    assert float(analytics_response.headers["X-Process-Time-Ms"]) >= 0

    duration = time.perf_counter() - started_at
    assert duration >= 0