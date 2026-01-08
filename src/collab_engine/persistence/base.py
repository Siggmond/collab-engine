from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from collab_engine.core.protocol.messages import Op


@dataclass(frozen=True)
class OpRecord:
    doc_id: str
    server_seq: int
    origin_client_id: str
    client_msg_id: str
    op: Op


class Persistence(Protocol):
    def append_op(self, record: OpRecord) -> None: ...

    def get_ops_since(self, doc_id: str, since_server_seq: int) -> list[OpRecord] | None: ...

    def get_latest_server_seq(self, doc_id: str) -> int: ...

    def get_snapshot_text(self, doc_id: str) -> tuple[str, int] | None: ...

    def store_snapshot_text(self, doc_id: str, server_seq: int, full_text: str) -> None: ...
