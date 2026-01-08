from __future__ import annotations

import threading
from dataclasses import dataclass
from typing import Dict, List

from collab_engine.persistence.base import OpRecord, Persistence


@dataclass
class _DocStore:
    last_seq: int
    ops: List[OpRecord]
    snapshot_text: str


class InMemoryPersistence(Persistence):
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._docs: Dict[str, _DocStore] = {}

    def append_op(self, record: OpRecord) -> None:
        with self._lock:
            ds = self._docs.setdefault(record.doc_id, _DocStore(last_seq=0, ops=[], snapshot_text=""))
            ds.ops.append(record)
            ds.last_seq = record.server_seq

    def get_ops_since(self, doc_id: str, since_server_seq: int) -> list[OpRecord] | None:
        with self._lock:
            ds = self._docs.get(doc_id)
            if ds is None:
                return []
            return [r for r in ds.ops if r.server_seq > since_server_seq]

    def get_latest_server_seq(self, doc_id: str) -> int:
        with self._lock:
            ds = self._docs.get(doc_id)
            return ds.last_seq if ds else 0

    def get_snapshot_text(self, doc_id: str) -> tuple[str, int] | None:
        with self._lock:
            ds = self._docs.get(doc_id)
            if ds is None:
                return None
            return (ds.snapshot_text, ds.last_seq)

    def store_snapshot_text(self, doc_id: str, server_seq: int, full_text: str) -> None:
        with self._lock:
            ds = self._docs.setdefault(doc_id, _DocStore(last_seq=0, ops=[], snapshot_text=""))
            ds.snapshot_text = full_text
            ds.last_seq = max(ds.last_seq, server_seq)
