"""
WebSocket endpoint for real-time UI updates.

Clients connect to /api/ws and authenticate with their bearer access token sent
as a ``Sec-WebSocket-Protocol`` subprotocol (``["sris-auth", <token>]``) rather
than a URL query param, so the JWT never appears in request URLs or access logs.
The server selects the ``sris-auth`` subprotocol in its handshake response.

Once authenticated, the server broadcasts data-change events to the client so
the UI can update without a full page refresh.

Events are emitted from anywhere in the system via
``app.services.events.emit_data_change``.
"""

import json
import logging

from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect, status
from sqlalchemy.orm import Session

from app.api.auth import get_user_from_token
from app.database import get_db
from app.services.websocket_manager import ws_manager

logger = logging.getLogger("sris.realtime")

router = APIRouter()

SUBPROTOCOL = "sris-auth"


def _token_from_subprotocol(websocket: WebSocket) -> str | None:
    header = websocket.headers.get("sec-websocket-protocol", "")
    parts = [p.strip() for p in header.split(",") if p.strip()]
    # The browser echoes the client's offered protocols in order, e.g.
    # "sris-auth, eyJhbGciOi..."
    if parts and parts[0] == SUBPROTOCOL and len(parts) > 1:
        return parts[1]
    return None


@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket, db: Session = Depends(get_db)):
    token = _token_from_subprotocol(websocket)
    if not token:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    try:
        user = get_user_from_token(token, db)
    except Exception:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    await websocket.accept(subprotocol=SUBPROTOCOL)
    ws_manager.connect(websocket, user.id, user.role.value)
    logger.info("WebSocket client connected: user_id=%s role=%s", user.id, user.role.value)
    try:
        await websocket.send_text(json.dumps({
            "event": "connected",
            "user_id": user.id,
            "role": user.role.value,
        }))
        # Keep the connection alive until the client disconnects. The client may
        # send periodic ping frames; we discard them.
        while True:
            try:
                await websocket.receive_text()
            except WebSocketDisconnect:
                break
    except WebSocketDisconnect:
        pass
    finally:
        ws_manager.disconnect(websocket)
        logger.info("WebSocket client disconnected: user_id=%s", user.id)
