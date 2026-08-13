"""
Integration tests for the /api/ws WebSocket endpoint (auth + lifecycle).
"""

import json

import pytest
from starlette.websockets import WebSocketDisconnect

from app.services.websocket_manager import ws_manager


def register_user(client, email="employer@example.com", role="employer"):
    response = client.post(
        "/api/auth/register",
        json={
            "email": email,
            "password": "Strong-password1",
            "full_name": "Test Employer",
            "role": role,
            "company_name": "SRIS Test Co",
        },
    )
    assert response.status_code == 201, response.text
    return response.json()


def login_tokens(client, email="employer@example.com"):
    response = client.post(
        "/api/auth/login",
        data={"username": email, "password": "Strong-password1"},
    )
    assert response.status_code == 200, response.text
    return response.json()


def test_ws_connect_with_valid_token_receives_connected(client):
    register_user(client, email="ws@example.com", role="employer")
    token = login_tokens(client, email="ws@example.com")["access_token"]

    with client.websocket_connect(f"/api/ws?token={token}") as ws:
        data = ws.receive_text()
        msg = json.loads(data)
        assert msg["event"] == "connected"
        assert msg["role"] == "employer"

    assert ws_manager.connection_count == 0


def test_ws_rejects_missing_token(client):
    with pytest.raises(Exception):
        with client.websocket_connect("/api/ws") as ws:
            ws.receive_text()
    assert ws_manager.connection_count == 0


def test_ws_rejects_invalid_token(client):
    with pytest.raises(Exception):
        with client.websocket_connect("/api/ws?token=not-a-real-token") as ws:
            ws.receive_text()
    assert ws_manager.connection_count == 0


def test_ws_accepts_employee_role(client):
    register_user(client, email="emp@example.com", role="employee")
    token = login_tokens(client, email="emp@example.com")["access_token"]

    with client.websocket_connect(f"/api/ws?token={token}") as ws:
        msg = json.loads(ws.receive_text())
        assert msg["event"] == "connected"
        assert msg["role"] == "employee"
