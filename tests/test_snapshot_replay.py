"""Tests for snapshot creation and replay correctness.

These tests validate that:
- Materializing state from the op log produces the same result as snapshots
- DocumentService can rebuild state from persistence and continue correctly

The persistence backend used here is in-memory and represents Phase 1 behavior.
"""

from collab_engine.core.crdt.rga import RGA
from collab_engine.core.protocol.messages import InsertOp
from collab_engine.persistence.memory import InMemoryPersistence
from collab_engine.services.document_service import DocumentService

import asyncio


def test_snapshot_equals_replay_from_oplog() -> None:
    """Snapshot text must match state reconstructed by replaying the op log."""

    persistence = InMemoryPersistence()
    svc = DocumentService(persistence=persistence)

    doc_id = "d1"

    op1 = InsertOp(type="ins", parent_id=(0, "root"), id=(1, "c1"), value="H")
    op2 = InsertOp(type="ins", parent_id=(1, "c1"), id=(2, "c1"), value="i")

    async def run() -> None:
        await svc.apply_op(doc_id=doc_id, origin_client_id="c1", client_msg_id="m1", op=op1)
        await svc.apply_op(doc_id=doc_id, origin_client_id="c1", client_msg_id="m2", op=op2)

    asyncio.run(run())

    snap_text, snap_seq = persistence.get_snapshot_text(doc_id) or ("", 0)
    assert snap_seq == persistence.get_latest_server_seq(doc_id)

    rga = RGA()
    ops = persistence.get_ops_since(doc_id=doc_id, since_server_seq=0) or []
    for rec in ops:
        rga.integrate(rec.op)

    assert rga.materialize() == snap_text


def test_service_rebuild_from_persistence_matches_snapshot() -> None:
    """Rebuilding service state from persistence must preserve correctness."""

    persistence = InMemoryPersistence()
    svc1 = DocumentService(persistence=persistence)

    doc_id = "d2"

    op1 = InsertOp(type="ins", parent_id=(0, "root"), id=(1, "c1"), value="A")
    op2 = InsertOp(type="ins", parent_id=(0, "root"), id=(1, "c2"), value="B")

    async def run() -> None:
        await svc1.apply_op(doc_id=doc_id, origin_client_id="c1", client_msg_id="m1", op=op1)
        await svc1.apply_op(doc_id=doc_id, origin_client_id="c2", client_msg_id="m2", op=op2)

    asyncio.run(run())

    snap_text, snap_seq = persistence.get_snapshot_text(doc_id) or ("", 0)

    # Simulate server restart by creating a new service instance
    svc2 = DocumentService(persistence=persistence)

    op3 = InsertOp(type="ins", parent_id=(0, "root"), id=(2, "c3"), value="C")

    async def run2() -> None:
        await svc2.apply_op(doc_id=doc_id, origin_client_id="c3", client_msg_id="m3", op=op3)

    asyncio.run(run2())

    snap_text2, snap_seq2 = persistence.get_snapshot_text(doc_id) or ("", 0)

    assert snap_seq2 == snap_seq + 1
    assert snap_text2 == "ABC"
