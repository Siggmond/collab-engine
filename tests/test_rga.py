"""Tests for the RGA (Replicated Growable Array) CRDT.

These tests validate the core correctness properties of the Phase 1 RGA
implementation, including determinism, buffering, tombstone behavior,
and idempotent replay.
"""

from collab_engine.core.crdt.rga import ROOT_ID, RGA
from collab_engine.core.protocol.messages import DeleteOp, InsertOp


def test_concurrent_inserts_same_parent_are_deterministic() -> None:
    """Concurrent inserts at the same parent must converge deterministically."""

    a = InsertOp(type="ins", parent_id=ROOT_ID, id=(1, "a"), value="A")
    b = InsertOp(type="ins", parent_id=ROOT_ID, id=(1, "b"), value="B")

    rga1 = RGA()
    rga1.integrate(b)
    rga1.integrate(a)

    rga2 = RGA()
    rga2.integrate(a)
    rga2.integrate(b)

    assert rga1.materialize() == "AB"
    assert rga2.materialize() == "AB"


def test_insert_before_parent_is_buffered_then_integrated() -> None:
    """Inserts referencing unknown parents must be buffered until resolved."""

    parent_id = (5, "p")
    parent = InsertOp(type="ins", parent_id=ROOT_ID, id=parent_id, value="P")
    child = InsertOp(type="ins", parent_id=parent_id, id=(6, "c"), value="c")

    rga = RGA()

    rga.integrate(child)
    assert rga.materialize() == ""

    rga.integrate(parent)
    assert rga.materialize() == "Pc"


def test_delete_before_insert_results_in_tombstone() -> None:
    """Deletes received before inserts must tombstone the future element."""

    target_id = (10, "x")
    delete_first = DeleteOp(type="del", id=target_id)
    insert_later = InsertOp(type="ins", parent_id=ROOT_ID, id=target_id, value="Z")

    rga = RGA()
    rga.integrate(delete_first)
    rga.integrate(insert_later)

    assert rga.materialize() == ""


def test_replay_idempotency() -> None:
    """Replaying the same operations must not change materialized state."""

    op1 = InsertOp(type="ins", parent_id=ROOT_ID, id=(1, "a"), value="A")
    op2 = InsertOp(type="ins", parent_id=(1, "a"), id=(2, "a"), value="B")
    op3 = DeleteOp(type="del", id=(1, "a"))

    rga = RGA()
    for op in (op1, op2, op3):
        rga.integrate(op)

    first = rga.materialize()

    for op in (op1, op2, op3):
        rga.integrate(op)

    second = rga.materialize()

    assert first == "B"
    assert second == "B"
