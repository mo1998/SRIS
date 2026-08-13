"""
Realtime event emission for live UI updates.

When something meaningful happens anywhere in the system (a new notification, a
completed evaluation, an interview status change, a recorded decision), the
relevant place calls ``emit_data_change(category, data)``. The event is then
delivered to every connected WebSocket client (see ``app/api/ws.py``) so the UI
updates without a page refresh.

Delivery path:
  1. ``emit_data_change`` publishes the event to a Redis pub/sub channel.
   2. The API process runs a background subscriber (``start_subscriber_daemon``,
     started in the app lifespan) that receives the event and forwards it to
     the locally-connected WebSocket clients via ``ws_manager``.

This works across processes: the RQ evaluation worker publishes an event and
the API process (which owns the WebSocket connections) forwards it to clients.

If Redis is unavailable (e.g. during tests or a degraded deploy), ``emit_data_change``
falls back to broadcasting directly to in-process WebSocket clients when a
running event loop is available, so locally-connected clients still update.
"""

import asyncio
import json
import logging
import threading
import time
from datetime import datetime
from typing import Any, Dict, Optional

import redis

from app.config import settings
from app.services.websocket_manager import ws_manager

logger = logging.getLogger("sris.realtime")
if not logger.handlers:
    _h = logging.StreamHandler()
    _h.setFormatter(
        logging.Formatter(
            "%(asctime)s [%(threadName)s] %(levelname)s %(name)s: %(message)s"
        )
    )
    logger.addHandler(_h)
    logger.setLevel(logging.INFO)

CHANNEL = "sris:realtime"

_redis_sync: Optional[redis.Redis] = None


def build_message(category: str, data: Dict[str, Any] | None = None) -> Dict[str, Any]:
    return {
        "event": "data_changed",
        "category": category,
        "data": data or {},
        "timestamp": datetime.utcnow().isoformat(),
    }


def _running_loop() -> Optional[asyncio.AbstractEventLoop]:
    try:
        return asyncio.get_running_loop()
    except RuntimeError:
        return None


def get_redis_sync() -> redis.Redis:
    global _redis_sync
    if _redis_sync is None:
        _redis_sync = redis.from_url(settings.REDIS_URL)
    return _redis_sync


def publish_to_redis(message: Dict[str, Any]) -> bool:
    """Publish an event to the realtime Redis channel. Returns success."""
    try:
        get_redis_sync().publish(CHANNEL, json.dumps(message, default=str))
        return True
    except Exception as exc:
        logger.warning("Realtime Redis publish failed: %s", exc)
        return False


def emit_data_change(category: str, data: Dict[str, Any] | None = None) -> None:
    """Emit a realtime data-change event for a system action.

    Publishes to Redis so the API process can forward it to WebSocket clients.
    If Redis is unavailable and there is a running event loop (the API process),
    fall back to broadcasting in-process so connected clients still update.
    """
    msg = build_message(category, data)
    if not publish_to_redis(msg):
        loop = _running_loop()
        if loop is not None:
            asyncio.ensure_future(
                ws_manager.broadcast_data_change(msg["category"], msg["data"]),
                loop=loop,
            )


_uv_loop: Optional[asyncio.AbstractEventLoop] = None
_stop_subscriber = threading.Event()


def configure_event_loop(loop: asyncio.AbstractEventLoop) -> None:
    """Capture the API process's uvicorn event loop so cross-loop broadcasts
    can be scheduled onto it (WS transports are bound to that loop)."""
    global _uv_loop
    _uv_loop = loop


async def handle_pubsub_message(raw: str) -> Dict[str, Any]:
    msg = json.loads(raw)
    category = msg.get("category", "unknown")
    data = msg.get("data") or {}
    if _uv_loop is not None:
        asyncio.run_coroutine_threadsafe(
            ws_manager.broadcast_data_change(category, data),
            _uv_loop,
        )
    else:
        await ws_manager.broadcast_data_change(category, data)
    return msg


def _subscriber_thread_main() -> None:
    """Run a synchronous ``redis`` pub/sub subscriber in a daemon thread.

    A dedicated thread (with its own blocking ``pubsub.listen()`` loop) is used
    instead of an ASGI lifespan task because, under gunicorn's multi-worker
    uvicorn workers, a task scheduled during lifespan startup does not reliably
    survive into the serving phase. The sync ``redis`` client + ``listen()``
    loop is also reliable here (the async ``redis.asyncio`` subscriber
    half-registers subscriptions on the deployed redis-py version).

    Received events are dispatched to WebSocket clients by scheduling the
    broadcast onto the API process's uvicorn event loop (``_uv_loop``) via
    ``run_coroutine_threadsafe``, because WebSocket transports are bound to
    that loop. One subscriber thread runs per gunicorn worker process.
    """
    logger.info("Realtime subscriber thread starting for channel '%s'", CHANNEL)
    while not _stop_subscriber.is_set():
        logger.info("Realtime subscriber connecting to %s", settings.REDIS_URL)
        client = None
        pubsub = None
        try:
            client = redis.from_url(settings.REDIS_URL)
            pubsub = client.pubsub()
            pubsub.subscribe(CHANNEL)
            logger.info("Realtime Redis subscriber started on '%s'", CHANNEL)
            for message in pubsub.listen():
                if _stop_subscriber.is_set():
                    break
                if not isinstance(message, dict) or message.get("type") != "message":
                    continue
                try:
                    raw = message.get("data")
                    if isinstance(raw, bytes):
                        raw = raw.decode("utf-8", errors="replace")
                    logger.debug(
                        "RECEIVED realtime message on '%s': %s", CHANNEL, raw[:120]
                    )
                    msg = json.loads(raw)
                    category = msg.get("category", "unknown")
                    data = msg.get("data") or {}
                    if _uv_loop is not None:
                        asyncio.run_coroutine_threadsafe(
                            ws_manager.broadcast_data_change(category, data),
                            _uv_loop,
                        )
                    else:
                        logger.warning(
                            "Realtime: no uv loop configured; discarding event"
                        )
                except Exception as exc:
                    logger.warning("Failed to handle realtime message: %s", exc)
        except Exception as exc:
            logger.warning("Realtime subscriber sync error: %s", exc)
        finally:
            if pubsub is not None:
                try:
                    pubsub.close()
                except Exception:
                    pass
            if client is not None:
                try:
                    client.close()
                except Exception:
                    pass
        if _stop_subscriber.is_set():
            break
        time.sleep(3)


def start_subscriber_daemon() -> threading.Thread:
    """Start the realtime subscriber as a daemon thread (one per worker process)."""
    thread = threading.Thread(
        target=_subscriber_thread_main,
        name="sris-realtime-subscriber",
        daemon=True,
    )
    thread.start()
    return thread
