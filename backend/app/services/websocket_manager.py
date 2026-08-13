"""
WebSocket connection manager for real-time UI updates.

Holds the in-process set of authenticated WebSocket connections and broadcasts
data-change events to them. The API process owns the WS clients; events that
originate in worker processes (e.g. evaluation completion in the RQ worker)
are routed here via Redis pub/sub (see app/services/events.py).
"""

import json
import logging
from datetime import datetime
from typing import Any, Dict, List

from fastapi import WebSocket

logger = logging.getLogger("sris.realtime")


class Connection:
    __slots__ = ("websocket", "user_id", "role")

    def __init__(self, websocket: WebSocket, user_id: int, role: str) -> None:
        self.websocket = websocket
        self.user_id = user_id
        self.role = role


class WebSocketManager:
    def __init__(self) -> None:
        self._connections: List[Connection] = []

    def connect(self, websocket: WebSocket, user_id: int, role: str) -> Connection:
        connection = Connection(websocket, user_id, role)
        self._connections.append(connection)
        return connection

    def disconnect(self, websocket: WebSocket) -> None:
        self._connections = [c for c in self._connections if c.websocket is not websocket]

    @property
    def connection_count(self) -> int:
        return len(self._connections)

    async def _send(self, websocket: WebSocket, message: Dict[str, Any]) -> bool:
        try:
            await websocket.send_text(json.dumps(message, default=str))
            return True
        except (Exception,):  # client gone
            self.disconnect(websocket)
            return False

    async def broadcast(self, message: Dict[str, Any]) -> int:
        if not self._connections:
            return 0
        sent = 0
        for conn in list(self._connections):
            if await self._send(conn.websocket, message):
                sent += 1
        return sent

    async def broadcast_data_change(self, category: str, data: Dict[str, Any] | None = None) -> int:
        message = {
            "event": "data_changed",
            "category": category,
            "data": data or {},
            "timestamp": datetime.utcnow().isoformat(),
        }
        return await self.broadcast(message)


ws_manager = WebSocketManager()
