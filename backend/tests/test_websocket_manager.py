"""
Tests for app.services.websocket_manager.WebsocketManager.
"""

import asyncio
import json

import pytest

from app.services.websocket_manager import WebSocketManager


class FakeWebSocket:
    """Minimal stand-in for a FastAPI WebSocket supporting send_text."""

    def __init__(self, fail: bool = False):
        self.messages = []
        self.closed = False
        self.fail = fail

    async def send_text(self, text: str) -> None:
        if self.fail:
            raise ConnectionError("client disconnected")
        self.messages.append(text)


def test_connect_and_disconnect():
    manager = WebSocketManager()
    ws = FakeWebSocket()
    manager.connect(ws, user_id=1, role="employer")
    assert manager.connection_count == 1
    manager.disconnect(ws)
    assert manager.connection_count == 0


def test_broadcast_reaches_all_connections():
    manager = WebSocketManager()
    ws_a = FakeWebSocket()
    ws_b = FakeWebSocket()
    manager.connect(ws_a, user_id=1, role="employer")
    manager.connect(ws_b, user_id=2, role="employee")

    sent = asyncio.run(manager.broadcast({"event": "data_changed", "category": "interview"}))

    assert sent == 2
    for ws in (ws_a, ws_b):
        assert len(ws.messages) == 1
        decoded = json.loads(ws.messages[0])
        assert decoded["event"] == "data_changed"
        assert decoded["category"] == "interview"


def test_broadcast_data_change_shape():
    manager = WebSocketManager()
    ws = FakeWebSocket()
    manager.connect(ws, user_id=1, role="employer")

    asyncio.run(manager.broadcast_data_change("notification", {"unread_count": 3}))

    decoded = json.loads(ws.messages[0])
    assert decoded["event"] == "data_changed"
    assert decoded["category"] == "notification"
    assert decoded["data"] == {"unread_count": 3}
    assert "timestamp" in decoded


def test_broadcast_removes_dead_connections():
    manager = WebSocketManager()
    ws_alive = FakeWebSocket()
    ws_dead = FakeWebSocket(fail=True)
    manager.connect(ws_alive, user_id=1, role="employer")
    manager.connect(ws_dead, user_id=2, role="employee")

    sent = asyncio.run(manager.broadcast({"event": "data_changed", "category": "decision"}))

    assert sent == 1
    assert manager.connection_count == 1
    assert ws_alive in [c.websocket for c in manager._connections]


@pytest.mark.asyncio
async def test_broadcast_no_connections_returns_zero():
    manager = WebSocketManager()
    assert await manager.broadcast_data_change("anything") == 0
