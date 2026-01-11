# Phase 2: Durable Persistence (PostgreSQL)

**Status:** Design Proposal  
**Phase 1:** Frozen (no behavioral changes)  
**Scope:** Durable storage, replay acceleration, restart recovery  
**Applies to:** Collab-Engine document state  
**Audience:** Contributors, system designers, reviewers  

This document proposes the **Phase 2 persistence design** for Collab-Engine.
Phase 1 behavior remains unchanged and is treated as the correctness baseline.

---

## Objectives

Phase 2 introduces durable persistence to:

- Make document state **survive server restarts**
- Support efficient **reconnect replay** using canonical `server_seq`
- **Bound replay cost** via periodic snapshots
- Preserve Phase 1 correctness and ordering guarantees

Durability must not weaken protocol safety or convergence properties.

---

## Core Principles

1. **Operation Log Is Authoritative**
   - The operation log is the source of truth
   - Snapshots are performance accelerators, not correctness dependencies

2. **Monotonic Ordering**
   - `server_seq` is strictly monotonic per document

3. **Idempotent Ingestion**
   - The persistence layer must safely handle duplicate operation delivery
   - Duplicate client submissions must not create duplicate effects

4. **Per-Document Isolation**
   - Persistence operations must respect per-document locking semantics

---

## Proposed PostgreSQL Schema

### `documents`

```sql
documents (
  doc_id TEXT PRIMARY KEY,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  head_server_seq BIGINT NOT NULL DEFAULT 0,
  epoch BIGINT NOT NULL DEFAULT 0
)
```

---

### `document_ops`

```sql
document_ops (
  doc_id TEXT NOT NULL REFERENCES documents(doc_id),
  server_seq BIGINT NOT NULL,
  origin_client_id TEXT NOT NULL,
  client_msg_id TEXT NOT NULL,
  op JSONB NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  PRIMARY KEY (doc_id, server_seq),
  UNIQUE (doc_id, origin_client_id, client_msg_id)
)
```

---

### `document_snapshots`

```sql
document_snapshots (
  doc_id TEXT NOT NULL REFERENCES documents(doc_id),
  snapshot_server_seq BIGINT NOT NULL,
  epoch BIGINT NOT NULL,
  crdt_state JSONB NULL,
  full_text TEXT NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  PRIMARY KEY (doc_id, snapshot_server_seq)
)
```

---

## Snapshot Strategy

Snapshots are produced using a **hybrid trigger model**:

- Operation-count trigger (e.g. every 1000 operations)
- Time-based trigger (e.g. at most once every 30 seconds for active documents)

Snapshots must be created at a stable `server_seq` under the per-document lock.

---

## Recovery Paths

### Client Reconnect

If `head_server_seq - last_seen_server_seq` is small enough, replay operations.
Otherwise send a snapshot and replay remaining operations.

### Server Restart

Load latest snapshot and replay ops up to `head_server_seq`.

---

## Snapshot Representation Options

- Text-only snapshot (simplest, more replay)
- CRDT-state snapshot (faster, requires versioning)

### Recommendation

Store both `full_text` and `crdt_state`, using `full_text` as a safe fallback.

---

## Notes

This document defines design intent only. Exact schema and triggers may evolve.
