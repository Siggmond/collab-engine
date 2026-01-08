from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from typing import Dict

from collab_engine.core.crdt.rga import RGA
from collab_engine.core.protocol.messages import Op
from collab_engine.persistence.base import OpRecord, Persistence


logger = logging.getLogger(__name__)


@dataclass
class _DocState:
    lock: asyncio.Lock
    crdt: RGA
    server_seq: int


class DocumentService:
    def __init__(self, persistence: Persistence) -> None:
        self._persistence = persistence
        self._docs: Dict[str, _DocState] = {}
        self._global_lock = asyncio.Lock()

    def get_server_seq(self, doc_id: str) -> int:
        return self._persistence.get_latest_server_seq(doc_id)

    async def apply_op(self, doc_id: str, origin_client_id: str, client_msg_id: str, op: Op) -> int:
        doc = await self._get_or_create_doc(doc_id)
        async with doc.lock:
            doc.server_seq += 1
            server_seq = doc.server_seq

            doc.crdt.integrate(op)
            full_text = doc.crdt.materialize()

            logger.info(
                "crdt integrated",
                extra={"doc_id": doc_id, "client_id": origin_client_id, "server_seq": server_seq},
            )

            self._persistence.append_op(
                OpRecord(
                    doc_id=doc_id,
                    server_seq=server_seq,
                    origin_client_id=origin_client_id,
                    client_msg_id=client_msg_id,
                    op=op,
                )
            )
            self._persistence.store_snapshot_text(doc_id=doc_id, server_seq=server_seq, full_text=full_text)

            return server_seq

    def get_snapshot(self, doc_id: str) -> tuple[str, int]:
        snap = self._persistence.get_snapshot_text(doc_id)
        if snap is None:
            return ("", 0)
        return snap

    async def _get_or_create_doc(self, doc_id: str) -> _DocState:
        async with self._global_lock:
            ds = self._docs.get(doc_id)
            if ds is not None:
                return ds

            crdt = RGA()
            server_seq = self._persistence.get_latest_server_seq(doc_id)
            ops = self._persistence.get_ops_since(doc_id=doc_id, since_server_seq=0) or []
            if ops:
                logger.info(
                    "crdt rebuild from oplog start",
                    extra={"doc_id": doc_id, "client_id": "-", "server_seq": server_seq},
                )
            for rec in ops:
                crdt.integrate(rec.op)
            full_text = crdt.materialize()
            self._persistence.store_snapshot_text(doc_id=doc_id, server_seq=server_seq, full_text=full_text)
            if ops:
                logger.info(
                    "crdt rebuild from oplog done",
                    extra={"doc_id": doc_id, "client_id": "-", "server_seq": server_seq},
                )

            ds = _DocState(lock=asyncio.Lock(), crdt=crdt, server_seq=server_seq)
            self._docs[doc_id] = ds
            return ds
