import httpx

from app.config import settings
from app.services.email_service import (
    EmailProviderError,
    MailpitEmailProvider,
    ResendEmailProvider,
    get_email_health,
    get_email_provider,
)


def test_email_health_reports_placeholder_configuration(monkeypatch):
    monkeypatch.setattr(settings, "EMAIL_PROVIDER", "mailpit")
    monkeypatch.setattr(settings, "MAILPIT_API_URL", "")
    monkeypatch.setattr(settings, "MAIL_FROM", "noreply@sris.com")

    health = get_email_health()

    assert health["configured"] is False
    assert health["status"] == "configuration_incomplete"
    assert set(health["missing_settings"]) == {"MAILPIT_API_URL", "MAIL_FROM"}
    assert health["provider"] == "mailpit"


def test_email_health_reports_configured(monkeypatch):
    monkeypatch.setattr(settings, "EMAIL_PROVIDER", "mailpit")
    monkeypatch.setattr(settings, "MAILPIT_API_URL", "http://localhost:8025/api/v1/send")
    monkeypatch.setattr(settings, "MAIL_FROM", "interviews@example.com")

    health = get_email_health()

    assert health["configured"] is True
    assert health["status"] == "configured"
    assert health["missing_settings"] == []
    assert health["provider"] == "mailpit"
    assert health["mail_server"] == "localhost"
    assert health["mail_port"] == 8025


def test_email_health_resend_configured(monkeypatch):
    monkeypatch.setattr(settings, "EMAIL_PROVIDER", "resend")
    monkeypatch.setattr(settings, "RESEND_API_KEY", "re_test123")
    monkeypatch.setattr(settings, "MAIL_FROM", "interviews@example.com")

    health = get_email_health()

    assert health["configured"] is True
    assert health["status"] == "configured"
    assert health["provider"] == "resend"
    assert health["missing_settings"] == []
    assert health["mail_server"] == "api.resend.com"
    assert health["mail_port"] == 443


def test_email_health_resend_missing_key(monkeypatch):
    monkeypatch.setattr(settings, "EMAIL_PROVIDER", "resend")
    monkeypatch.setattr(settings, "RESEND_API_KEY", "")
    monkeypatch.setattr(settings, "MAIL_FROM", "interviews@example.com")

    health = get_email_health()

    assert health["configured"] is False
    assert health["status"] == "configuration_incomplete"
    assert health["missing_settings"] == ["RESEND_API_KEY"]


def test_email_health_disabled(monkeypatch):
    monkeypatch.setattr(settings, "EMAIL_PROVIDER", "disabled")

    health = get_email_health()

    assert health["configured"] is False
    assert health["status"] == "disabled"
    assert health["provider"] == "disabled"
    assert health["missing_settings"] == []


def test_resend_provider_sends_expected_payload(monkeypatch):
    monkeypatch.setattr(settings, "EMAIL_PROVIDER", "resend")
    monkeypatch.setattr(settings, "RESEND_API_KEY", "re_test123")
    monkeypatch.setattr(settings, "MAIL_FROM", "interviews@example.com")
    monkeypatch.setattr(settings, "MAIL_FROM_NAME", "SRIS")
    captured = []

    def fake_post(url, headers=None, json=None, timeout=None):
        captured.append({"url": url, "headers": headers or {}, "json": json})
        return httpx.Response(200, request=httpx.Request("POST", url))

    monkeypatch.setattr("app.services.email_service.httpx.post", fake_post)

    ResendEmailProvider().send("candidate@example.com", "Candidate", "Subject", "<p>body</p>")

    assert captured[0]["url"] == "https://api.resend.com/emails"
    assert captured[0]["headers"]["Authorization"] == "Bearer re_test123"
    assert captured[0]["json"]["from"] == "SRIS <interviews@example.com>"
    assert captured[0]["json"]["to"] == ["candidate@example.com"]
    assert captured[0]["json"]["subject"] == "Subject"
    assert captured[0]["json"]["html"] == "<p>body</p>"


def test_resend_provider_requires_api_key(monkeypatch):
    monkeypatch.setattr(settings, "EMAIL_PROVIDER", "resend")
    monkeypatch.setattr(settings, "RESEND_API_KEY", "")

    try:
        ResendEmailProvider().send("candidate@example.com", "Candidate", "Subject", "<p>body</p>")
        assert False, "expected EmailProviderError"
    except EmailProviderError:
        pass


def test_mailpit_provider_sends_legacy_payload(monkeypatch):
    monkeypatch.setattr(settings, "EMAIL_PROVIDER", "mailpit")
    monkeypatch.setattr(settings, "MAILPIT_API_URL", "http://localhost:8025/api/v1/send")
    monkeypatch.setattr(settings, "MAIL_FROM", "interviews@example.com")
    monkeypatch.setattr(settings, "MAIL_FROM_NAME", "SRIS")
    captured = []

    def fake_post(url, headers=None, json=None, timeout=None):
        captured.append({"url": url, "json": json})
        return httpx.Response(200, request=httpx.Request("POST", url))

    monkeypatch.setattr("app.services.email_service.httpx.post", fake_post)

    MailpitEmailProvider().send("candidate@example.com", "Candidate", "Subject", "<p>body</p>")

    assert captured[0]["url"] == "http://localhost:8025/api/v1/send"
    assert captured[0]["json"]["From"] == {"Email": "interviews@example.com", "Name": "SRIS"}
    assert captured[0]["json"]["To"] == [{"Email": "candidate@example.com", "Name": "Candidate"}]


def test_send_retries_transient_failure_then_succeeds(monkeypatch):
    monkeypatch.setattr(settings, "EMAIL_PROVIDER", "mailpit")
    monkeypatch.setattr(settings, "MAILPIT_API_URL", "http://localhost:8025/api/v1/send")
    monkeypatch.setattr(settings, "MAIL_FROM", "interviews@example.com")
    monkeypatch.setattr("app.services.email_service.time.sleep", lambda _seconds: None)
    calls = []

    def flaky_post(url, headers=None, json=None, timeout=None):
        calls.append(1)
        request = httpx.Request("POST", url)
        if len(calls) == 1:
            return httpx.Response(429, request=request)
        return httpx.Response(200, request=request)

    monkeypatch.setattr("app.services.email_service.httpx.post", flaky_post)

    MailpitEmailProvider().send("candidate@example.com", "Candidate", "Subject", "<p>body</p>")

    assert len(calls) == 2


def test_get_email_provider_unknown_value_raises(monkeypatch):
    monkeypatch.setattr(settings, "EMAIL_PROVIDER", "carrier-pigeon")

    try:
        get_email_provider()
        assert False, "expected EmailProviderError"
    except EmailProviderError:
        pass


def test_completion_email_escapes_candidate_input(monkeypatch):
    """User-controlled names/titles must be HTML-escaped in the completion email."""
    import asyncio

    from app.services.email_service import send_completion_email

    monkeypatch.setattr(settings, "EMAIL_PROVIDER", "mailpit")
    monkeypatch.setattr(settings, "MAILPIT_API_URL", "http://localhost:8025/api/v1/send")
    monkeypatch.setattr(settings, "MAIL_FROM", "interviews@example.com")
    monkeypatch.setattr(settings, "MAIL_FROM_NAME", "SRIS")
    captured = []

    def fake_post(url, headers=None, json=None, timeout=None):
        captured.append({"json": json})
        return httpx.Response(200, request=httpx.Request("POST", url))

    monkeypatch.setattr("app.services.email_service.httpx.post", fake_post)

    asyncio.run(send_completion_email(
        to_email="candidate@example.com",
        candidate_name="<img src=x onerror=alert(1)>",
        interview_title="Support & Sales",
        score=80.0,
        passed=True,
        results_link="https://example.com/results?a=1&b=2",
    ))

    html = captured[0]["json"]["HTML"]
    assert "<img src=x onerror=alert(1)>" not in html
    assert "&lt;img src=x onerror=alert(1)&gt;" in html
    assert "Support &amp; Sales" in html
    assert "&amp;b=2" in html
