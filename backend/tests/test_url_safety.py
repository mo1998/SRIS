import os

import pytest


@pytest.fixture(autouse=True)
def _prod_mode():
    os.environ["DEBUG"] = "False"
    from app.config import settings
    old = settings.DEBUG
    settings.DEBUG = False
    yield
    settings.DEBUG = old


def test_rejects_private_ip_literal():
    from app.services.url_safety import validate_outbound_url

    assert validate_outbound_url("http://169.254.169.254/v1") is not None
    assert validate_outbound_url("http://127.0.0.1:8100/v1") is not None
    assert validate_outbound_url("http://10.0.0.1/v1") is not None
    assert validate_outbound_url("http://192.168.1.1/v1") is not None


def test_rejects_http_in_production_unless_allowlisted():
    from app.services.url_safety import validate_outbound_url

    assert validate_outbound_url("http://example.com/v1", allow_http_local=False) is not None
    assert validate_outbound_url("https://example.com/v1", allow_http_local=False) is None
    # local-model is allowlisted for the LLM base URL path
    assert validate_outbound_url("http://local-model:8100/v1", allow_http_local=True) is None


def test_rejects_embedded_credentials_and_bad_scheme():
    from app.services.url_safety import validate_outbound_url

    assert validate_outbound_url("https://user:pass@example.com/v1") is not None
    assert validate_outbound_url("file:///etc/passwd") is not None
    assert validate_outbound_url("ftp://example.com/v1") is not None


def test_allows_public_https():
    from app.services.url_safety import validate_outbound_url

    assert validate_outbound_url("https://api.openai.com/v1") is None
    assert validate_outbound_url("https://generativelanguage.googleapis.com/v1beta/openai") is None


def test_llm_settings_rejects_private_url(client):
    register = client.post(
        "/api/auth/register",
        json={"email": "ssrf@example.com", "password": "Strong-password1", "full_name": "SSRF", "role": "employer", "company_name": "SSRF Co"},
    )
    assert register.status_code == 201, register.text
    login = client.post("/api/auth/login", data={"username": "ssrf@example.com", "password": "Strong-password1"})
    token = login.json()["access_token"]

    patch = client.patch(
        "/api/users/me/organization/settings",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "evaluation_provider": "cloud_llm",
            "evaluation_model": "m",
            "evaluation_base_url": "http://169.254.169.254/v1",
            "evaluation_api_key": "sk",
        },
    )
    assert patch.status_code == 422, patch.text
