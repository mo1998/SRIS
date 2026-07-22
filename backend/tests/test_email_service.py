from app.config import settings
from app.services.email_service import get_email_health


def test_email_health_reports_placeholder_configuration(monkeypatch):
    monkeypatch.setattr(settings, "MAILPIT_API_URL", "")
    monkeypatch.setattr(settings, "MAIL_FROM", "noreply@sris.com")

    health = get_email_health()

    assert health["configured"] is False
    assert health["status"] == "configuration_incomplete"
    assert set(health["missing_settings"]) == {"MAILPIT_API_URL", "MAIL_FROM"}


def test_email_health_reports_configured(monkeypatch):
    monkeypatch.setattr(settings, "MAILPIT_API_URL", "http://localhost:8025/api/v1/send")
    monkeypatch.setattr(settings, "MAIL_FROM", "interviews@example.com")

    health = get_email_health()

    assert health["configured"] is True
    assert health["status"] == "configured"
    assert health["missing_settings"] == []
    assert health["provider"] == "mailpit"
