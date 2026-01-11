# Phase 2 Design Plan

**Status:** Design Plan (Docs Only)  
**Phase 1:** Approved and Frozen  
**Scope:** Persistence, compaction, presence, auth boundaries (design only)  
**Audience:** Contributors, reviewers, system designers  

This document defines the **Phase 2 design plan** for Collab-Engine.
Phase 1 behavior, semantics, protocol concepts, and implementation are **locked**
and must not be modified by Phase 2 work.

All Phase 2 changes must be introduced behind **clear system boundaries** so that
the CRDT correctness core remains unchanged.

---

## Phase 1 Invariants (Must Hold)

The following invariants are preserved without exception:

- `server_seq` is the canonical per-document ordering for persistence, replay, and observability
- Clients may apply operations optimistically but must tolerate receiving their own operations back from the server
- The text CRDT remains an **RGA-style sequence CRDT** with deterministic ordering of concurrent inserts

---

## 1. Goals and Non-Goals

### Goals

#### Durable Persistence (PostgreSQL)
- Append-only authoritative operation log ordered by `server_seq`
- Periodic snapshots to bound recovery and replay cost
- Deterministic reconstruction of document state after server restart

#### Operational Recovery & Correctness
- On startup, reconstruct state from snapshot + op log
- On reconnect, replay since `last_seen_server_seq` or resync via snapshot

#### Tombstone Growth Management
- Define a **safe compaction strategy** (design only in Phase 2)

#### Presence and Cursors
- Real-time presence and cursor updates
- Must not affect CRDT correctness or persistence

#### Authentication / Authorization Boundary
- Enforce auth at API and session boundaries
- No coupling of auth logic into CRDT internals

#### Observability
- Structured logs and metrics for persistence and recovery paths (design-level)

---

### Non-Goals (Explicit)

- Rich text or formatting
- UI or client rendering concerns
- Multi-region replication
- Horizontal scaling of WebSocket rooms
- Client undo/redo complexity
- CRDT algorithm replacement (RGA remains)

---

## 2. Persistence Design (PostgreSQL)

### Core Principles

- Operation log is the **source of truth**
- Snapshots are performance accelerators
- `server_seq` is authoritative and monotonic per document
- Persistence must be idempotent (client retries must not duplicate effects)
- Storage formats must be forward-compatible

---

### Proposed Schema

#### `documents`

```sql
doc_id TEXT PRIMARY KEY
created_at TIMESTAMPTZ NOT NULL DEFAULT now()
head_server_seq BIGINT NOT NULL DEFAULT 0
epoch BIGINT NOT NULL DEFAULT 0
```

Notes:
- `epoch` is reserved for compaction schemes that invalidate historical identifiers

---

#### `document_ops`

Append-only operation log.

```sql
doc_id TEXT NOT NULL REFERENCES documents(doc_id)
server_seq BIGINT NOT NULL
origin_client_id TEXT NOT NULL
client_msg_id TEXT NOT NULL
op JSONB NOT NULL
created_at TIMESTAMPTZ NOT NULL DEFAULT now()
PRIMARY KEY (doc_id, server_seq)
UNIQUE (doc_id, origin_client_id, client_msg_id)
```

Indexes:
- `(doc_id, server_seq)` via primary key
- Optional `(doc_id, created_at)` for analytics

---

#### `document_snapshots`

```sql
doc_id TEXT NOT NULL REFERENCES documents(doc_id)
snapshot_server_seq BIGINT NOT NULL
epoch BIGINT NOT NULL
crdt_state JSONB NULL
full_text TEXT NOT NULL
created_at TIMESTAMPTZ NOT NULL DEFAULT now()
PRIMARY KEY (doc_id, snapshot_server_seq)
```

Indexes:
- `(doc_id, snapshot_server_seq DESC)` for latest snapshot lookup

---

### Snapshot Frequency

Two complementary policies:

- **Operation-count based:** snapshot every N ops (e.g. N = 1000)
- **Time-based:** at most one snapshot per T seconds (e.g. T = 30s)

Snapshots must be produced:
- Per document
- Under the per-document lock
- At a stable `server_seq`

---

### Replay Strategy

#### Client Reconnect

- If `head_server_seq - last_seen_server_seq <= replay_max_ops`:
  - Replay operations
- Else:
  - Send latest snapshot
  - Replay remaining operations since snapshot

---

#### Server Restart

- Load latest snapshot
- Replay operations from snapshot to head
- Resume serving

---

### Snapshot Representation

#### Text-Only Snapshot
- Decoupled from CRDT internals
- Requires more replay

#### CRDT-State Snapshot
- Faster startup
- Requires versioned compatibility

**Recommendation:**  
Store both `full_text` and `crdt_state`.  
Treat `crdt_state` as an optimization with safe fallback to op-log rebuild.

---

## 3. Tombstone GC / Compaction

### Problem

RGA tombstones accumulate, increasing:

- In-memory size
- Snapshot size
- Replay cost

Phase 2 defines strategy only; implementation requires explicit approval.

---

### Level A: Conservative Pruning

- No epoch change
- Remove tombstones only when provably safe

Conditions may include:
- Element is a leaf
- Element is causally stable for all clients

Risk:
- Incorrect stability assumptions

Mitigation:
- Force resync on unresolved references

---

### Level B: Epoch-Based Compaction

- Aggressive reclamation
- Explicitly invalidates old identifiers

Mechanism:
- Create compacted snapshot
- Increment `documents.epoch`
- Reject operations from older epochs
- Force resync on mismatch

---

### Failure Modes

- Client references GC’d id:
  - Conservative: resync
  - Epoch-based: expected → resync
- Partial compaction:
  - Must be transactional
- Compaction vs ops:
  - Must run under per-document lock

---

## 4. Presence and Cursors

### Principle

Presence is **ephemeral metadata** and must never:
- Affect CRDT integration
- Be persisted in the op log

---

### Model

Maintained in the Session subsystem:
- Per-document room state
- Per-client cursor and selection

Suggested WS messages:
- `presence_update`
- `presence_snapshot`

---

### Cursor Representation

Avoid index-based cursors.  
Prefer CRDT-anchored cursors:

```json
{
  "anchor_id": "ElementId",
  "affinity": "left | right"
}
```

Selections are defined by two cursors.

---

## 5. Authentication Boundary

### Where Auth Applies

- FastAPI / WS handshake: authentication
- Session / DocumentService:
  - authorize join (read)
  - authorize apply_op (write)

---

### CRDT Isolation Rule

CRDT logic must never:
- Understand users, roles, or permissions
- Depend on auth or identity concepts

---

### Persistence & Auditing

Persist origin identifiers for observability:
- Map `origin_client_id` to user
- Or store `origin_user_id` separately

---

## 6. Risks and Open Questions

### Correctness

- Client lamport persistence across restarts
- Message id strategy (UUID vs monotonic)

---

### Epoch Compaction

- Acceptable disruption level
- Maximum offline client staleness

---

### Persistence

- Write amplification on hot documents
- Snapshot compression
- Op-log retention policy

---

### Scaling (Future)

- Multi-node fanout via pub/sub
- Non-goal for Phase 2, but must not be blocked
