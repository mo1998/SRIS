import pytest

from app.config import Settings, validate_production_settings


def test_debug_settings_allow_development_defaults():
    settings = Settings(DEBUG=True)

    validate_production_settings(settings)


def test_production_settings_reject_insecure_secret_key():
    settings = Settings(
        DEBUG=False,
        SECRET_KEY="your-secret-key-change-in-production",
        ALLOWED_ORIGINS=["https://sris.example.com"],
        EVALUATION_QUEUE_BACKEND="rq",
    )

    with pytest.raises(RuntimeError, match="SECRET_KEY"):
        validate_production_settings(settings)


def test_production_settings_reject_localhost_origins():
    settings = Settings(
        DEBUG=False,
        SECRET_KEY="a-secure-production-secret-key-value",
        ALLOWED_ORIGINS=["http://localhost:3000"],
        EVALUATION_QUEUE_BACKEND="rq",
    )

    with pytest.raises(RuntimeError, match="localhost"):
        validate_production_settings(settings)


def test_production_settings_reject_background_evaluation_queue():
    settings = Settings(
        DEBUG=False,
        SECRET_KEY="a-secure-production-secret-key-value",
        ALLOWED_ORIGINS=["https://sris.example.com"],
        EVALUATION_QUEUE_BACKEND="background",
    )

    with pytest.raises(RuntimeError, match="EVALUATION_QUEUE_BACKEND"):
        validate_production_settings(settings)


def test_production_settings_accept_secure_values():
    settings = Settings(
        DEBUG=False,
        SECRET_KEY="a-secure-production-secret-key-value",
        ALLOWED_ORIGINS=["https://sris.example.com"],
        EVALUATION_QUEUE_BACKEND="rq",
    )

    validate_production_settings(settings)