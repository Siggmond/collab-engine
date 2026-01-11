# collab-engine

[![Python](https://img.shields.io/badge/Python-3.x-3776AB?logo=python&logoColor=white)](https://github.com/topics/python)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.x-009688?logo=fastapi&logoColor=white)](https://github.com/topics/fastapi)
[![WebSockets](https://img.shields.io/badge/WebSockets-Real--Time-4353FF)](https://github.com/topics/websocket)
[![CRDT](https://img.shields.io/badge/CRDT-Deterministic%20Merge-000000)](https://github.com/topics/crdt)
[![Distributed Systems](https://img.shields.io/badge/Distributed%20Systems-Correctness--First-2F3136)](https://github.com/topics/distributed-systems)
[![Testing](https://img.shields.io/badge/pytest-Test%20Suite-0A9EDC?logo=pytest&logoColor=white)](https://github.com/topics/pytest)
[![Docs](https://img.shields.io/badge/Docs-Architecture%20%26%20Protocol-4B5563)](https://github.com/topics/documentation)
[![Postgres (Phase 2)](https://img.shields.io/badge/PostgreSQL-Phase%202%20Design-4169E1?logo=postgresql&logoColor=white)](https://github.com/topics/postgresql)
[![Phase 1](https://img.shields.io/badge/Phase%201-Locked%20%26%20Tested-16A34A)](#)

A **production-grade real-time collaboration backend** (Google Docs–style core) built with **Python** and **FastAPI**.  
The system implements a **deterministic text CRDT** to safely merge concurrent edits over **WebSockets**, with correctness-first **replay / resync semantics** and a clearly documented path to durable persistence.

---

## Project Status

### Phase 1 — Core Collaboration Engine (Current)
- ✔ Implemented
- ✔ Covered by automated tests
- ✔ Deterministic and correctness-focused
- ✔ **Frozen / locked** (no further behavioral changes)

### Phase 2 — Operational Evolution (Design Only)
- 📄 Architecture & design documents available under `docs/`
- ❌ Intentionally **not implemented** to preserve Phase 1 correctness guarantees

---

## Preview / Screenshots

> The following screenshots demonstrate protocol correctness, real-time fan-out, and recovery behavior.  
> No UI is involved — all screenshots are taken from WebSocket clients and server logs.

### WebSocket Handshake
![WebSocket Handshake](docs/screenshots/04-ws-handshake.png)
_Client connects via WebSocket and completes the mandatory `hello → hello_ack` handshake, followed by an initial snapshot (`resync`)._

### Real-Time Collaboration (Two Clients)
![Two Clients Receiving Updates](docs/screenshots/05-two-clients.png)
_Two independent WebSocket clients connected to the same document receive the same `op_echo` messages in real time._

### Deterministic Concurrent Inserts (CRDT)
![Deterministic Concurrent Inserts](docs/screenshots/06-concurrent-inserts.jpeg)
_Concurrent inserts targeting the same position converge deterministically across clients using total ordering on `(lamport, replica_id)`._

### Replay on Reconnect
![Replay on Reconnect](docs/screenshots/07-replay.jpeg)
_A client reconnects with `last_seen_server_seq`; the server replays only the missing operations from the op log._

### Snapshot Resync (Fallback)
![Snapshot Resync](docs/screenshots/08-resync.png)
_When replay is not possible, the server safely falls back to a full snapshot resync to re-establish a correct baseline._

---

## Architecture Overview

### Components
- **CRDT Core** — RGA-style sequence CRDT for collaborative text
- **Transport Layer** — WebSocket-based real-time messaging
- **Session Management** — per-document rooms and client fan-out
- **Persistence Layer** — operation log + snapshots  
  *(Phase 1: in-memory reference implementation)*
- **API Layer** — FastAPI (HTTP + WebSocket)

### End-to-End Data Flow
1. Client connects via WebSocket and sends `hello`
2. Server responds with `hello_ack` and chooses:
   - op-log replay, or
   - full snapshot resync
3. Client sends `op` messages (insert / delete)
4. Server:
   - integrates via CRDT
   - assigns authoritative `server_seq`
   - appends to op log
   - broadcasts `op_echo` to all connected clients (including origin)

---

## CRDT Model

Phase 1 uses an **RGA-style sequence CRDT**:

- Insert-after semantics using `parent_id`
- Concurrent inserts at the same position are ordered deterministically by:
  ```
  (lamport, replica_id)
  ```
- Deletes are represented as tombstones
- Missing dependencies are buffered until resolved

Detailed invariants and trade-offs are documented in:  
📄 [`docs/crdt.md`](docs/crdt/crdt.md)

---

## WebSocket Protocol

- Strict handshake (`hello` → `hello_ack`)
- Authoritative server sequencing (`server_seq`)
- Replay-on-reconnect and snapshot fallback
- Deterministic broadcast via `op_echo`

Full protocol specification:  
📄 [`docs/protocol.md`](docs/protocol/protocol.md)

---

## Running Locally

### Install dependencies
```bash
pip install -r requirements.txt
```

### Run the server
```bash
uvicorn collab_engine.main:app --app-dir src --host 0.0.0.0 --port 8000
```

### Endpoints
- Health check: `GET /health`
- WebSocket endpoint: `WS /ws`

---

## Tests

Core correctness guarantees are covered by automated tests:

- Deterministic ordering of concurrent inserts
- Tombstone handling and idempotent replay
- Snapshot equivalence with op-log replay
- Service rebuild from persistence

Run tests with:
```bash
pytest
```

---

## Phase 2 (Design Highlights)

Phase 2 is **explicitly design-only** and documents realistic next steps without modifying Phase 1 behavior:

- PostgreSQL-backed persistence
- Snapshot frequency and replay bounding
- Tombstone compaction strategies
- Presence and cursor model
- Authentication / authorization boundaries

All Phase 2 documents live under `docs/`.

---

## Notes

- Phase 1 persistence is intentionally **in-memory**; restarting the server clears state.
- This repository focuses on **correctness, determinism, and protocol clarity**, not UI concerns.
- Designed as a backend system component suitable for collaborative editors, tooling, or research prototypes.

---

## License

MIT
