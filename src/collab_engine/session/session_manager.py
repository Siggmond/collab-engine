from __future__ import annotations

import asyncio
import json
import logging
from dataclasses import dataclass, field
from typing import Any, Dict, Set

from fastapi import WebSocket

logger = logging.getLogger(__name__)


@dataclass(eq=False)
class Connection:
    websocket: WebSocket
    client_id: str
    send_queue: asyncio.Queue[str] = field(default_factory=lambda: asyncio.Queue(maxsize=256))
    closed: bool = False

    async def send_json(self, payload: dict[str, Any]) -> None:
        if self.closed:
            return
        msg = json.dumps(payload, separators=(",", ":"))
        try:
            self.send_queue.put_nowait(msg)
        except asyncio.QueueFull:
            self.close()
            try:
                await self.websocket.close(code=1013)
            except Exception:
                pass

    async def writer_loop(self) -> None:
        while not self.closed:
            msg = await self.send_queue.get()
            try:
                await self.websocket.send_text(msg)
            except Exception:
                self.close()

    def close(self) -> None:
        self.closed = True


class SessionManager:
    def __init__(self) -> None:
        self._lock = asyncio.Lock()
        self._doc_rooms: Dict[str, Set[Connection]] = {}
        self._conn_to_doc: Dict[Connection, str] = {}

    async def join(self, doc_id: str, connection: Connection) -> None:
        async with self._lock:
            room = self._doc_rooms.setdefault(doc_id, set())
            room.add(connection)
            self._conn_to_doc[connection] = doc_id

    async def leave_any(self, connection: Connection) -> None:
        async with self._lock:
            doc_id = self._conn_to_doc.pop(connection, None)
            if doc_id is None:
                return
            room = self._doc_rooms.get(doc_id)
            if room is not None:
                room.discard(connection)
                if not room:
                    self._doc_rooms.pop(doc_id, None)

    async def broadcast(self, doc_id: str, message: dict[str, Any]) -> None:
        async with self._lock:
            conns = list(self._doc_rooms.get(doc_id, set()))

        for c in conns:
            await c.send_json(message)
