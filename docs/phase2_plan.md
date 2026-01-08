# Phase 2 Design Plan (docs only)

## Status: Phase 1 frozen

Phase 1 is **approved and locked**.

- No changes to Phase 1 behavior, semantics, protocol concepts, or implementation are part of this plan.
- Phase 2 work must be introduced behind clear system boundaries so the CRDT correctness core remains unchanged.

The Phase 1 invariants remain:
- `server_seq` is the canonical per-document ordering for persistence, replay, and observability.
- Clients may apply operations optimistically but must tolerate receiving their own operations back from the server.
- The text CRDT remains an RGA-style sequence CRDT with deterministic ordering of concurrent inserts.

---

## 1) Goals and non-goals

### Goals

- **Durable persistence** using PostgreSQL:
  - Append-only authoritative operation log ordered by `server_seq`.
  - Periodic snapshots to bound recovery and replay.
  - Deterministic reconstruction of document state after server restart.
- **Operational recovery and correctness**:
  - On startup, reconstruct from snapshot + op log and resume serving.
  - On reconnect, replay since client’s `last_seen_server_seq` or resync via snapshot.
- **Tombstone growth management**:
  - Define and implement a safe compaction strategy (design only here).
- **Presence and cursors**:
  - Provide real-time presence/cursor updates without affecting CRDT correctness.
- **Authentication/authorization boundary**:
  - Add auth checks at API/session edges without coupling into the CRDT core.
- **Observability for persistence/recovery paths**:
  - Structured logs and metrics for durability operations (design-level here).

### Non-goals (explicit)

- No rich text / formatting.
- No UI concerns.
- No multi-region replication.
- No multi-node horizontal scaling of WebSocket rooms (Phase 2 may create seams, not deliver HA).
- No client undo/redo complexity.
- No CRDT algorithm swap (keep RGA for Phase 2).

---

## 2) Persistence design (PostgreSQL)

### Core principles

- **Op log is the source of truth**, snapshots are accelerators.
- `server_seq` is authoritative, monotonic per document.
- Persistence must support **idempotent ingestion** (client retries cannot duplicate operations).
- Storage formats must be forward-compatible:
  - ops stored as `jsonb`.
  - snapshots can store both `full_text` and optionally a serialized CRDT state blob.

### Schema (proposed)

#### `documents`

Document metadata and the current head sequence.

- `doc_id TEXT PRIMARY KEY`
- `created_at TIMESTAMPTZ NOT NULL DEFAULT now()`
- `head_server_seq BIGINT NOT NULL DEFAULT 0`
- `epoch BIGINT NOT NULL DEFAULT 0`

Notes:
- `epoch` is reserved for compaction schemes that invalidate historical element identifiers.

#### `document_ops`

Append-only op log.

- `doc_id TEXT NOT NULL REFERENCES documents(doc_id)`
- `server_seq BIGINT NOT NULL`
- `origin_client_id TEXT NOT NULL`
- `client_msg_id TEXT NOT NULL`
- `op JSONB NOT NULL`
- `created_at TIMESTAMPTZ NOT NULL DEFAULT now()`
- `PRIMARY KEY (doc_id, server_seq)`
- `UNIQUE (doc_id, origin_client_id, client_msg_id)`

Indexes:
- `(doc_id, server_seq)` implied by PK.
- Optional `(doc_id, created_at)` for analytics.

#### `document_snapshots`

Snapshots for bounding replay.

- `doc_id TEXT NOT NULL REFERENCES documents(doc_id)`
- `snapshot_server_seq BIGINT NOT NULL`
- `epoch BIGINT NOT NULL`
- `crdt_state JSONB NULL`
- `full_text TEXT NOT NULL`
- `created_at TIMESTAMPTZ NOT NULL DEFAULT now()`
- `PRIMARY KEY (doc_id, snapshot_server_seq)`

Indexes:
- `(doc_id, snapshot_server_seq DESC)` for latest snapshot.

### Snapshot frequency

Two policies (can be combined):

- **Op-count based**: snapshot every `N` ops per document (e.g., `N = 1000`).
- **Time-based**: at most one snapshot per `T` seconds per active document (e.g., `T = 30s`).

Snapshot triggers must be per-document, evaluated under the per-document lock to avoid producing snapshots that don’t correspond to a stable `server_seq`.

### Replay strategy

#### Reconnect replay

Client reconnects with `last_seen_server_seq`.

Server chooses:
- If `head_server_seq - last_seen_server_seq <= replay_max_ops`:
  - query `document_ops` for `(last_seen_server_seq, head_server_seq]` and replay.
- Else:
  - send latest snapshot (or a snapshot nearest to head), and replay remaining ops since snapshot.

#### Server restart recovery

On startup (or lazily per document):
- Load latest snapshot `(snapshot_server_seq)`.
- Replay ops from `(snapshot_server_seq, head_server_seq]`.

### Snapshot representation: `crdt_state` vs text-only

- **Text-only snapshot**:
  - Pros: decoupled from internal CRDT representation.
  - Cons: cannot reconstruct CRDT without replaying full op log.

- **CRDT-state snapshot (`crdt_state`)**:
  - Pros: faster startup and lower replay CPU.
  - Cons: snapshot format/versioning becomes a compatibility surface.

Recommendation:
- Store both `full_text` and `crdt_state`.
- Treat `crdt_state` as an optimization:
  - If decoding fails/version mismatch, rebuild from op log and overwrite snapshot.

---

## 3) Tombstone GC / compaction

### Problem statement

RGA uses tombstones for deletion. Tombstones accumulate over time, increasing:
- in-memory size
- snapshot size
- replay cost

Phase 2 must define a safe strategy; it may be implemented in Phase 2 only with explicit approval.

### Safety conditions

Two levels of compaction are identified with different safety bars.

#### Level A: conservative pruning (no epoch change)

Goal: physically remove tombstones only when provably unnecessary without invalidating identifiers.

A conservative rule set may require:
- tombstoned element is a **leaf** (no children)
- and element is **causally stable** with respect to all clients that could later reference it

Stability signals:
- For connected clients: maintain per-connection `last_seen_server_seq`.
- For disconnected clients: either persist checkpoints or accept that very stale clients may be forced to resync.

Risk:
- If stability is incorrectly assumed, a client may later reference a removed id.

Mitigation:
- Treat unresolved references as requiring resync (or protocol violation depending on contract).

#### Level B: compaction with epoch bump (effective reclamation)

Goal: aggressively compact state and explicitly invalidate prior identifiers.

Mechanism:
- Create a compacted snapshot representing only the current visible sequence.
- Increment `documents.epoch`.
- Require clients to include `epoch` in `hello` and `op`.
- If epoch mismatch:
  - server responds with snapshot resync for current epoch
  - server rejects ops from old epoch

This is the most robust approach for long-lived documents.

### Trade-offs

- Conservative pruning:
  - safer/less disruptive, but may reclaim little.
- Epoch compaction:
  - reclaim is strong and predictable, but introduces an epoch compatibility contract.

### Failure modes

- **Client references GC’d id**:
  - With conservative pruning: should not happen if stability is correct; otherwise force resync.
  - With epoch compaction: expected on mismatch; resync.

- **Partial compaction persisted**:
  - Must be transactional: new snapshot + epoch update atomically.

- **Compaction races with ops**:
  - Must run under the per-document lock and only compact at a stable `server_seq`.

---

## 4) Presence and cursors (kept out of CRDT correctness)

### Principle

Presence is ephemeral metadata and must never:
- affect CRDT integration
- be persisted into the op log

### Model

Presence is maintained in the Session subsystem:
- per-doc room state
- per-client cursor + selection

Suggested WS message types (conceptual):
- `presence_update`
- `presence_snapshot` (sent on join)

### Cursor representation

Avoid index-based cursors (they drift under concurrent edits). Prefer CRDT-anchored cursors:

- Cursor: `{ anchor_id: ElementId, affinity: "left"|"right" }`
- Selection: `{ start: Cursor, end: Cursor }`

If clients can only provide indices initially, treat it as best-effort and map to nearest anchor.

---

## 5) Auth boundary (without contaminating core logic)

### Where auth plugs in

- **FastAPI/API layer**:
  - authenticate WS handshake
  - create a `Principal` (user_id, org, roles)

- **Session/DocumentService boundary**:
  - enforce authorization on join (read)
  - enforce authorization on apply_op (write)

### What CRDT must never do

- CRDT code must not understand users, roles, orgs, permissions.
- CRDT must remain purely about deterministic operation integration.

### Persistence linkage

Persist identifiers for auditing and observability:
- either fold `user_id` into `origin_client_id` mapping
- or store a separate `origin_user_id` column

---

## 6) Risks and open questions

### Correctness / protocol

- **ElementId policy**:
  - Requirement: client lamport counter must be monotonic.
  - Open question: how do we handle client restarts and lamport persistence?

- **Idempotency contract**:
  - `(doc_id, origin_client_id, client_msg_id)` must be unique.
  - Open question: do we enforce UUID vs monotonic msg ids?

- **Epoch compaction contract**:
  - How disruptive can compaction be?
  - What is the expected maximum staleness for offline clients?

### Persistence/ops

- **Write amplification** on hot documents.
  - Likely need batching/async persistence (design only in Phase 2).

- **Snapshot size**.
  - Might require compression later.

- **Retention**.
  - Open question: do we keep op log forever for history, or truncate before snapshot?

### Scaling

- Multi-node fanout requires pub/sub (Redis/NATS) and consistent doc routing.
- Non-goal for Phase 2, but design should not block future introduction.
