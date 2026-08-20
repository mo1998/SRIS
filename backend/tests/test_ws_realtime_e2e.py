"""
End-to-end: an authenticated action pushes a data_changed event over the
WebSocket to a connected client (realtime, no page reload).

Uses the in-process fallback (Redis publish mocked unavailable) so it runs in
CI without a live Redis; the Redis->subscriber forwarding is covered by
test_events.py and the WS delivery path by this test.
"""

import json

import pytest

from app.services import events
from app.database import SessionLocal
from app.models import Notification, User
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


def test_action_pushes_data_changed_to_ws_client(client, monkeypatch, wait_ws_disconnect):
    user = register_user(client, email="e2e@example.com", role="employer")
    token = login_tokens(client, email="e2e@example.com")["access_token"]

    db = SessionLocal()
    try:
        db.add(Notification(user_id=user["id"], type="general", title="Hello"))
        db.commit()
        notification_id = db.query(Notification).filter(Notification.user_id == user["id"]).first().id
    finally:
        db.close()

    # Force the in-process broadcast fallback (no Redis in the test process).
    monkeypatch.setattr(events, "publish_to_redis", lambda message: False)

    with client.websocket_connect("/api/ws", subprotocols=["sris-auth", token]) as ws:
        assert json.loads(ws.receive_text())["event"] == "connected"

        resp = client.post(
            f"/api/notifications/{notification_id}/read",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200, resp.text

        msg = json.loads(ws.receive_text())
        assert msg["event"] == "data_changed"
        assert msg["category"] == "notification"

    wait_ws_disconnect(ws_manager, 0)
