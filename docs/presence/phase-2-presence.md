# Phase 2: Presence and Cursors

**Status:** Design Proposal  
**Phase 1:** Frozen (no behavioral changes)  
**Scope:** Presence, cursors, and selection metadata  
**Applies to:** Collab-Engine session layer  
**Audience:** Contributors, system designers, reviewers  

This document proposes the **Phase 2 presence and cursor design** for
Collab-Engine. Phase 1 behavior remains unchanged and is treated as the
correctness baseline.

Presence is intentionally kept **outside** the CRDT correctness core.

---

## Design Principles

Presence data is **ephemeral metadata**. It must never:

- Affect CRDT integration or convergence
- Be persisted into the operation log
- Influence ordering, replay, or recovery logic

CRDT correctness must remain fully independent from presence state.

---

## Session-Layer Model

Presence is managed entirely within the **Session subsystem**.

### Responsibilities

- Track per-document room membership
- Track per-client cursor and selection state
- Broadcast presence updates to connected clients

Presence state is discarded on disconnect and rebuilt dynamically.

---

## Message Types (Conceptual)

The following WebSocket message types are suggested:

- `presence_update`
  - Sent by clients when cursor or selection changes
- `presence_snapshot`
  - Sent by the server on join
  - Represents the current presence state of the document

These messages are **not** part of the CRDT protocol.

---

## Cursor Representation

### Motivation

Index-based cursors drift under concurrent edits and cannot be relied upon
for stable positioning.

---

### CRDT-Anchored Cursors (Recommended)

Cursors are anchored to CRDT element identifiers:

```json
{
  "anchor_id": "ElementId",
  "affinity": "left | right"
}
```

- `anchor_id` refers to a CRDT element
- `affinity` determines cursor bias when edits occur near the anchor

---

### Selection Representation

Selections are defined by two cursors:

```json
{
  "start": { "anchor_id": "...", "affinity": "left" },
  "end": { "anchor_id": "...", "affinity": "right" }
}
```

This representation remains stable under concurrent inserts and deletes.

---

## Best-Effort Index Mapping

If a client can only provide **index-based cursors**:

- The server or client may map indices to the nearest CRDT anchors
- Mapping is treated as **best-effort**
- Minor visual drift is acceptable
- CRDT correctness must not depend on mapping accuracy

---

## Design Rationale

This design ensures:

- Presence does not contaminate the correctness core
- Cursor positioning remains stable under concurrency
- Presence can evolve independently of persistence and replay logic

---

## Notes

- Presence is not persisted
- Presence state is rebuilt on reconnect
- This document defines design intent only
