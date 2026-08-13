"""
WebSocket endpoint for real-time UI updates.

Clients connect to /api/ws with their bearer access token as a query param
(``token=``), the same token used for authenticated HTTP requests. Once
authenticated, the server broadcasts data-change events to the client so the
UI can update without a full page refresh.

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


@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket, db: Session = Depends(get_db)):
    token = websocket.query_params.get("token")
    if not token:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    try:
        user = get_user_from_token(token, db)
    except Exception:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    await websocket.accept()
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
