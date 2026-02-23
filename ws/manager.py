"""WebSocket connection pool and broadcast manager."""
from __future__ import annotations

import asyncio
import json
import logging
from typing import Any

from fastapi import WebSocket

logger = logging.getLogger(__name__)


class WSManager:
    def __init__(self):
        self._connections: list[WebSocket] = []
        self._lock = asyncio.Lock()

    async def connect(self, ws: WebSocket):
        await ws.accept()
        async with self._lock:
            self._connections.append(ws)
        logger.info(f"WS connected. Total: {len(self._connections)}")

    async def disconnect(self, ws: WebSocket):
        async with self._lock:
            if ws in self._connections:
                self._connections.remove(ws)
        logger.info(f"WS disconnected. Total: {len(self._connections)}")

    async def broadcast(self, data: dict):
        """Broadcast JSON-serializable dict to all connected clients."""
        if not self._connections:
            return
        message = json.dumps(data, ensure_ascii=False)
        dead: list[WebSocket] = []
        async with self._lock:
            connections = list(self._connections)

        for ws in connections:
            try:
                await ws.send_text(message)
            except Exception:
                dead.append(ws)

        if dead:
            async with self._lock:
                for ws in dead:
                    if ws in self._connections:
                        self._connections.remove(ws)

    async def send_to(self, ws: WebSocket, data: dict):
        try:
            await ws.send_text(json.dumps(data, ensure_ascii=False))
        except Exception as e:
            logger.warning(f"send_to failed: {e}")

    @property
    def connection_count(self) -> int:
        return len(self._connections)
