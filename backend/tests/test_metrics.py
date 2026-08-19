import httpx
import pytest
from prometheus_client import REGISTRY

from app.config import settings
from app.services.evaluation_service import BaselineEvaluationProvider, CloudLLMEvaluationProvider


def _counter(name, labels=None):
    return REGISTRY.get_sample_value(name, labels or {}) or 0.0


def test_metrics_endpoint_exposes_prometheus_format(client):
    response = client.get("/metrics")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/plain")
    assert "sris_email_failures_total" in response.text
    assert "sris_email_sent_total" in response.text
    assert "sris_llm_fallbacks_total" in response.text
    assert "sris_rq_queue_depth" in response.text
    assert "sris_rq_failed_jobs" in response.text
    assert "sris_rq_workers" in response.text


def test_metrics_tracks_http_requests(client):
    client.get("/health")
    response = client.get("/metrics")

    assert response.status_code == 200
    assert "http_requests_total" in response.text


def test_metrics_endpoint_survives_unreachable_redis(client, monkeypatch):
    monkeypatch.setattr(settings, "REDIS_URL", "redis://127.0.0.1:1")

    response = client.get("/metrics")

    assert response.status_code == 200
    assert "sris_rq_workers" in response.text


def test_email_failure_increments_metric(client, monkeypatch):
    monkeypatch.setattr(settings, "EMAIL_PROVIDER", "mailpit")
    monkeypatch.setattr(settings, "MAILPIT_API_URL", "http://localhost:8025/api/v1/send")
    monkeypatch.setattr(settings, "MAIL_FROM", "interviews@example.com")
    monkeypatch.setattr("app.services.email_service.time.sleep", lambda _seconds: None)

    def broken_post(url, headers=None, json=None, timeout=None):
        raise httpx.ConnectError("mail transport unavailable", request=httpx.Request("POST", url))

    monkeypatch.setattr("app.services.email_service.httpx.post", broken_post)

    from app.services.email_service import send_reminder_email_sync

    before = _counter("sris_email_failures_total", {"provider": "mailpit"})
    result = send_reminder_email_sync(
        "candidate@example.com",
        "Candidate",
        "Subject",
        "Interview",
        __import__("datetime").datetime.utcnow(),
        1,
    )
    after = _counter("sris_email_failures_total", {"provider": "mailpit"})

    assert result is False
    assert after == before + 1


def test_email_success_increments_sent_metric(client, monkeypatch):
    monkeypatch.setattr(settings, "EMAIL_PROVIDER", "mailpit")
    monkeypatch.setattr(settings, "MAILPIT_API_URL", "http://localhost:8025/api/v1/send")
    monkeypatch.setattr(settings, "MAIL_FROM", "interviews@example.com")

    def ok_post(url, headers=None, json=None, timeout=None):
        return httpx.Response(200, request=httpx.Request("POST", url))

    monkeypatch.setattr("app.services.email_service.httpx.post", ok_post)

    from app.services.email_service import send_reminder_email_sync

    before = _counter("sris_email_sent_total", {"provider": "mailpit"})
    result = send_reminder_email_sync(
        "candidate@example.com",
        "Candidate",
        "Subject",
        "Interview",
        __import__("datetime").datetime.utcnow(),
        1,
    )
    after = _counter("sris_email_sent_total", {"provider": "mailpit"})

    assert result is True
    assert after == before + 1


@pytest.mark.asyncio
async def test_llm_fallback_increments_metric(monkeypatch):
    class BrokenAsyncClient:
        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

        async def post(self, *args, **kwargs):
            raise httpx.ConnectError("llm unreachable", request=httpx.Request("POST", "http://llm"))

    monkeypatch.setattr("app.services.evaluation_service.httpx.AsyncClient", lambda **kwargs: BrokenAsyncClient())

    provider = CloudLLMEvaluationProvider(
        BaselineEvaluationProvider(),
        model="gpt-test",
        base_url="https://api.cloud.test/v1",
        api_key="sk-test",
    )
    labels = {"from_provider": "cloud_llm", "to_provider": "deterministic_baseline"}
    before = _counter("sris_llm_fallbacks_total", labels)

    result = await provider.evaluate_answer("a solid answer", "the expected answer")
    after = _counter("sris_llm_fallbacks_total", labels)

    assert result.score is not None
    assert "used fallback" in result.feedback
    assert after == before + 1


def test_metrics_disabled_registers_no_endpoint(monkeypatch):
    from fastapi import FastAPI
    from fastapi.testclient import TestClient

    from app.metrics import setup_metrics

    monkeypatch.setattr(settings, "METRICS_ENABLED", False)

    fresh_app = FastAPI()
    setup_metrics(fresh_app)
    with TestClient(fresh_app) as test_client:
        assert test_client.get("/metrics").status_code == 404
