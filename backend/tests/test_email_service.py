from app.config import settings
from app.services.email_service import get_email_health


def test_email_health_reports_placeholder_configuration(monkeypatch):
    monkeypatch.setattr(settings, "MAIL_FROM", "noreply@yourdomain.com")
    monkeypatch.setattr(settings, "MAIL_PASSWORD", "your-email-password")
    monkeypatch.setattr(settings, "MAIL_SERVER", "smtp.gmail.com")

    health = get_email_health()

    assert health["configured"] is False
    assert health["status"] == "configuration_incomplete"
    assert set(health["missing_settings"]) == {"MAIL_FROM", "MAIL_PASSWORD", "MAIL_SERVER"}


def test_email_health_reports_configured_smtp(monkeypatch):
    monkeypatch.setattr(settings, "MAIL_FROM", "interviews@example.com")
    monkeypatch.setattr(settings, "MAIL_PASSWORD", "smtp-secret")
    monkeypatch.setattr(settings, "MAIL_SERVER", "smtp.example.com")
    monkeypatch.setattr(settings, "MAIL_PORT", 587)

    health = get_email_health()

    assert health["configured"] is True
    assert health["status"] == "configured"
    assert health["missing_settings"] == []