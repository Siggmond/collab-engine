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

Tracks document-level metadata.

```sql
documents (
  doc_id TEXT PRIMARY KEY,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  head_server_seq BIGINT NOT NULL DEFAULT 0,
  epoch BIGINT NOT NULL DEFAULT 0
)
document_ops
Append-only operation log.

sql
Copy code
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
Properties:

Enforces global ordering via (doc_id, server_seq)

Ensures idempotency via (doc_id, origin_client_id, client_msg_id)

Supports deterministic replay

document_snapshots
Accelerates recovery and replay.

sql
Copy code
document_snapshots (
  doc_id TEXT NOT NULL REFERENCES documents(doc_id),
  snapshot_server_seq BIGINT NOT NULL,
  epoch BIGINT NOT NULL,
  crdt_state JSONB NULL,
  full_text TEXT NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  PRIMARY KEY (doc_id, snapshot_server_seq)
)
Snapshots are optional accelerators and must always correspond to a stable
server_seq.

Snapshot Strategy
Snapshots are produced using a hybrid trigger model:

Operation-count trigger (e.g. every 1000 operations)

Time-based trigger (e.g. at most once every 30 seconds for active documents)

Snapshots must be created:

At a stable server_seq

Under the per-document lock

Atomically (no partial persistence)

Recovery Paths
Client Reconnect (Replay)
Given a client last_seen_server_seq:

If head_server_seq - last_seen_server_seq is within replay bounds:

Replay operations since last_seen_server_seq

Otherwise:

Send latest snapshot

Replay remaining operations after snapshot

Server Restart
On server startup:

Load the latest snapshot per document

Replay operations from snapshot_server_seq to head_server_seq

Resume normal operation

Snapshot Representation Options
Text-Only Snapshot
Stores only full_text

Simplest representation

Requires more replay work

CRDT-State Snapshot
Stores serialized CRDT internal state

Faster recovery

Requires versioning discipline

Recommendation
Store both representations:

full_text as the safe fallback

crdt_state as an optimization

If CRDT versioning mismatches or state is invalid:

Rebuild from operation log using full_text

Design Rationale
Phase 2 persistence is designed to:

Preserve Phase 1 invariants

Make durability explicit and auditable

Separate correctness from performance optimizations

Enable future phases (e.g. compaction, epochs) safely

Notes
This document defines design intent only

Exact schema and triggers may evolve during implementation

Any deviation must preserve ordering, idempotency, and replay guarantees
