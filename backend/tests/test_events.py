"""
Tests for app.services.events: emit routing + Redis subscriber bridge.
"""

import asyncio
import json
from unittest import mock

import pytest

from app.services import events
from app.services.websocket_manager import ws_manager


def test_build_message_shape():
    msg = events.build_message("notification", {"unread_count": 2})
    assert msg["event"] == "data_changed"
    assert msg["category"] == "notification"
    assert msg["data"] == {"unread_count": 2}
    assert "timestamp" in msg


@pytest.mark.asyncio
async def test_emit_data_change_falls_back_in_process_when_redis_unavailable():
    with mock.patch.object(events, "publish_to_redis", return_value=False), \
         mock.patch.object(ws_manager, "broadcast_data_change", new_callable=mock.AsyncMock) as spy:
        events.emit_data_change("interview", {"interview_id": 5})
        await asyncio.sleep(0)
        spy.assert_awaited_once_with("interview", {"interview_id": 5})


@pytest.mark.asyncio
async def test_emit_data_change_does_not_broadcast_when_redis_available():
    with mock.patch.object(events, "publish_to_redis", return_value=True), \
         mock.patch.object(ws_manager, "broadcast_data_change", new_callable=mock.AsyncMock) as spy:
        events.emit_data_change("interview", {"interview_id": 5})
        await asyncio.sleep(0)
        spy.assert_not_called()


def test_publish_to_redis_sends_to_channel():
    fake_redis = mock.MagicMock()
    with mock.patch.object(events, "get_redis_sync", return_value=fake_redis):
        assert events.publish_to_redis(events.build_message("decision", {"id": 1})) is True
    fake_redis.publish.assert_called_once()
    channel, raw = fake_redis.publish.call_args.args
    assert channel == events.CHANNEL
    parsed = json.loads(raw)
    assert parsed["category"] == "decision"
    assert parsed["data"] == {"id": 1}


def test_publish_to_redis_swallows_connection_failure():
    with mock.patch.object(events, "get_redis_sync", side_effect=ConnectionError("down")):
        assert events.publish_to_redis({"event": "x"}) is False


@pytest.mark.asyncio
async def test_handle_pubsub_message_forwards_to_manager():
    raw = json.dumps(events.build_message("decision", {"response_id": 1}))
    with mock.patch.object(ws_manager, "broadcast_data_change", new_callable=mock.AsyncMock) as spy:
        await events.handle_pubsub_message(raw)
    spy.assert_awaited_once_with("decision", {"response_id": 1})


@pytest.mark.asyncio
async def test_handle_pubsub_message_defaults_unknown_category():
    raw = json.dumps({"event": "data_changed", "data": {}})
    with mock.patch.object(ws_manager, "broadcast_data_change", new_callable=mock.AsyncMock) as spy:
        result = await events.handle_pubsub_message(raw)
    spy.assert_awaited_once_with("unknown", {})
    assert result["event"] == "data_changed"
