# Phase 2: Presence and Cursors

## Phase 1 is frozen

This document proposes Phase 2 presence/cursor design only. Phase 1 behavior remains unchanged.

---

## Design principle

Presence is **ephemeral metadata**. It must not:
- affect CRDT integration
- be persisted into the op log

CRDT correctness must be independent from presence state.

---

## Session-layer model

Presence lives in the Session subsystem:
- per-doc room members
- per-client cursor/selection

Suggested message types (conceptual):
- `presence_update`
- `presence_snapshot`

---

## Cursor representation

Index-based cursors drift under concurrent edits.
Prefer CRDT-anchored cursors:

- Cursor: `{ anchor_id: ElementId, affinity: "left"|"right" }`
- Selection: `{ start: Cursor, end: Cursor }`

If the client can only provide indices, treat mapping as best-effort.
