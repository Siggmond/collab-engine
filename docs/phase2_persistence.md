# Phase 2: Persistence (PostgreSQL)

## Phase 1 is frozen

This document proposes Phase 2 persistence design only. Phase 1 behavior remains unchanged.

---

## Objectives

- Make document state durable across server restarts.
- Support reconnect replay using canonical `server_seq`.
- Bound replay cost via snapshots.

---

## Data model principles

- **Op log is authoritative**; snapshots are accelerators.
- `server_seq` is monotonic per document.
- Persistence must handle **idempotent operation ingestion**.

---

## Postgres schema (proposed)

### `documents`

- `doc_id TEXT PRIMARY KEY`
- `created_at TIMESTAMPTZ NOT NULL DEFAULT now()`
- `head_server_seq BIGINT NOT NULL DEFAULT 0`
- `epoch BIGINT NOT NULL DEFAULT 0`

### `document_ops`

- `doc_id TEXT NOT NULL REFERENCES documents(doc_id)`
- `server_seq BIGINT NOT NULL`
- `origin_client_id TEXT NOT NULL`
- `client_msg_id TEXT NOT NULL`
- `op JSONB NOT NULL`
- `created_at TIMESTAMPTZ NOT NULL DEFAULT now()`
- `PRIMARY KEY (doc_id, server_seq)`
- `UNIQUE (doc_id, origin_client_id, client_msg_id)`

### `document_snapshots`

- `doc_id TEXT NOT NULL REFERENCES documents(doc_id)`
- `snapshot_server_seq BIGINT NOT NULL`
- `epoch BIGINT NOT NULL`
- `crdt_state JSONB NULL`
- `full_text TEXT NOT NULL`
- `created_at TIMESTAMPTZ NOT NULL DEFAULT now()`
- `PRIMARY KEY (doc_id, snapshot_server_seq)`

---

## Snapshot frequency

Combine:
- op-count trigger (e.g., every 1000 ops)
- time trigger (e.g., at most once per 30 seconds for active docs)

Snapshots must be produced at a stable `server_seq` under the per-doc lock.

---

## Recovery paths

### Reconnect replay

- If `head_server_seq - last_seen_server_seq` is small enough, replay ops since `last_seen_server_seq`.
- Otherwise send snapshot + replay remaining ops since snapshot.

### Server restart

- Load latest snapshot.
- Replay ops from snapshot seq to head.

---

## Snapshot representation options

- Text-only snapshot: simplest but needs more replay.
- CRDT-state snapshot: faster but requires versioning.

Recommendation:
- Store both `full_text` and `crdt_state`, treating `crdt_state` as an optimization with safe fallback to op-log rebuild.
