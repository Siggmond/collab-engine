from __future__ import annotations

"""RGA-style (Replicated Growable Array) sequence CRDT.

This implementation is intentionally minimal (Phase 1) but aims to be explicit about
correctness properties.

## Core model

- Elements are identified by a globally unique `ElementId` (lamport, replica_id).
- Inserts are expressed as "insert-after" by specifying a `parent_id`.
- Deletes are tombstones (logical deletion).

## Determinism

Concurrent inserts after the same `parent_id` are ordered by the total ordering on
`ElementId` (Python tuple ordering of `(lamport: int, replica_id: str)`), making the
resulting sequence deterministic across replicas given the same set of operations.

## Buffering safety

Operations may arrive out of causal order.

- If an insert arrives before its `parent_id` exists locally, it is buffered under
  `_pending_inserts[parent_id]` until the parent is integrated.
- If a delete arrives before the target id exists locally, it is buffered in
  `_pending_deletes` until the id is integrated.

Buffering is safe because:

- Integration is idempotent (re-applying an already-integrated op is a no-op).
- Buffered ops are immutable; once dependencies arrive, integrating them yields the
  same result as if they had arrived in causal order.
"""

from dataclasses import dataclass
from typing import Dict, List, Set

from collab_engine.core.protocol.messages import DeleteOp, ElementId, InsertOp, Op


ROOT_ID: ElementId = (0, "root")


@dataclass(frozen=True)
class _Node:
    id: ElementId
    parent_id: ElementId
    value: str
    deleted: bool = False


class RGA:
    """A minimal RGA sequence CRDT.

    ## Invariants (must always hold after `integrate` returns)

    - **Root existence**: `ROOT_ID` exists in `_nodes` and in `_children`.
    - **Parent existence for integrated nodes**: for every `node_id != ROOT_ID` in
      `_nodes`, `node.parent_id` is also present in `_nodes`.
      (If the parent is missing, the insert must remain buffered and must not create
      a node yet.)
    - **Children index completeness**: every id present in `_nodes` has a
      corresponding key in `_children`.
    - **Children lists are deterministic**: for each parent, `_children[parent]` is
      sorted ascending and contains no duplicates. This is the core determinism rule
      for concurrent inserts at the same parent.
    - **Tombstone monotonicity**: once a node is marked deleted, it never becomes
      non-deleted.
    - **Pending structures only reference missing dependencies**:
      - `_pending_inserts` keys are parent ids not (yet) present in `_nodes` at the
        time they were buffered.
      - `_pending_deletes` contains ids not present in `_nodes` at the time they were
        buffered.
    """

    def __init__(self) -> None:
        # TODO(phase2): Use chunked inserts (strings) instead of single-character inserts to reduce overhead.
        # TODO(phase2): Implement tombstone compaction / garbage collection once causal stability is tracked.
        self._nodes: Dict[ElementId, _Node] = {ROOT_ID: _Node(id=ROOT_ID, parent_id=ROOT_ID, value="", deleted=True)}
        self._children: Dict[ElementId, List[ElementId]] = {ROOT_ID: []}

        self._pending_inserts: Dict[ElementId, List[InsertOp]] = {}
        self._pending_deletes: Set[ElementId] = set()

    def integrate(self, op: Op) -> None:
        """Integrate a single CRDT operation.

        Post-condition: the state invariants documented on the class hold.

        This method is safe to call multiple times with the same operation.
        """
        if isinstance(op, InsertOp):
            self._integrate_insert(op)
            if __debug__:
                self._assert_invariants()
            return
        if isinstance(op, DeleteOp):
            self._integrate_delete(op)
            if __debug__:
                self._assert_invariants()
            return
        raise TypeError("unknown op")

    def materialize(self) -> str:
        """Materialize the current sequence as plain text."""
        out: list[str] = []
        self._dfs(ROOT_ID, out)
        return "".join(out)

    def has(self, element_id: ElementId) -> bool:
        """Return True iff the element id is integrated (not merely buffered)."""
        return element_id in self._nodes

    def _assert_invariants(self) -> None:
        if ROOT_ID not in self._nodes:
            raise AssertionError("ROOT_ID missing from nodes")
        if ROOT_ID not in self._children:
            raise AssertionError("ROOT_ID missing from children")

        for node_id, node in self._nodes.items():
            if node_id != ROOT_ID and node.parent_id not in self._nodes:
                raise AssertionError(f"missing parent for integrated node: {node_id} -> {node.parent_id}")
            if node_id not in self._children:
                raise AssertionError(f"children index missing key for node: {node_id}")

        for parent_id, kids in self._children.items():
            if kids != sorted(kids):
                raise AssertionError(f"children list not sorted for parent: {parent_id}")
            if len(kids) != len(set(kids)):
                raise AssertionError(f"children list contains duplicates for parent: {parent_id}")

    def _integrate_insert(self, op: InsertOp) -> None:
        if op.id in self._nodes:
            return

        if op.parent_id not in self._nodes:
            self._pending_inserts.setdefault(op.parent_id, []).append(op)
            return

        self._nodes[op.id] = _Node(id=op.id, parent_id=op.parent_id, value=op.value, deleted=False)
        self._children.setdefault(op.id, [])

        siblings = self._children.setdefault(op.parent_id, [])
        siblings.append(op.id)
        siblings.sort()

        if op.id in self._pending_deletes:
            self._pending_deletes.remove(op.id)
            self._tombstone(op.id)

        pending = self._pending_inserts.pop(op.id, None)
        if pending:
            for child in pending:
                self._integrate_insert(child)

    def _integrate_delete(self, op: DeleteOp) -> None:
        if op.id not in self._nodes:
            self._pending_deletes.add(op.id)
            return
        self._tombstone(op.id)

    def _tombstone(self, element_id: ElementId) -> None:
        n = self._nodes[element_id]
        if n.deleted:
            return
        self._nodes[element_id] = _Node(id=n.id, parent_id=n.parent_id, value=n.value, deleted=True)

    def _dfs(self, parent_id: ElementId, out: list[str]) -> None:
        for child_id in self._children.get(parent_id, []):
            node = self._nodes.get(child_id)
            if node is None:
                continue
            if not node.deleted:
                out.append(node.value)
            self._dfs(child_id, out)
