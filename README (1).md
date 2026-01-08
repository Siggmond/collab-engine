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

A production-grade real-time collaboration backend (Google Docs–style core) built with Python and FastAPI.  
The system implements a deterministic text CRDT to safely merge concurrent edits over WebSockets, with correctness-first replay/resync semantics and a documented path to durable persistence.

---

## Project Status

**Phase 1 — Core collaboration engine**
- ✔ Implemented
- ✔ Tested
- ✔ Deterministic and correctness-focused
- ✔ Locked (no further changes planned)

**Phase 2 — Operational evolution**
- 📄 Design only (see `docs/`)
- ❌ Not implemented by design

---

## Architecture

**Components**
- **Collaboration Engine** — CRDT core logic (sequence CRDT for text)
- **Transport Layer** — WebSocket-based real-time communication
- **Session Management** — connected clients, per-document rooms
- **Persistence Layer** — operation log + snapshots  
  *(Phase 1: in-memory implementation)*
- **API Layer** — FastAPI

**Data flow**
- Clients connect via WebSocket and send `hello`
- Server responds with `hello_ack` and selects replay or snapshot strategy
- Clients optimistically apply local operations and send `op`
- Server integrates via CRDT, assigns `server_seq`, appends to op log, and broadcasts `op_echo` to all clients (including origin)

---

## CRDT

Phase 1 uses an RGA-style sequence CRDT:
- Inserts reference a `parent_id` (insert-after semantics)
- Concurrent inserts after the same parent are deterministically ordered by `(lamport, replica_id)`
- Deletes are represented as tombstones

See [`docs/crdt.md`](docs/crdt.md) for details and invariants.

---

## WebSocket Protocol

Protocol message types, validation rules, and recovery behavior are documented in  
[`docs/protocol.md`](docs/protocol.md).

---

## Running

Install dependencies:

```bash
pip install -r requirements.txt
```

Run the server:

```bash
uvicorn collab_engine.main:app --app-dir src --host 0.0.0.0 --port 8000
```

Health check:
- `GET /health`

WebSocket endpoint:
- `WS /ws`

---

## Notes

- Phase 1 persistence is intentionally in-memory; restarting the server clears state.
- Phase 2 evolution (Postgres persistence, snapshot strategy, tombstone compaction, presence, auth boundaries) is fully documented under `docs/` and intentionally not implemented to preserve a frozen, correctness-focused core.
