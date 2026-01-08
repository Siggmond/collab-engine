# collab-engine

[![Python](https://img.shields.io/badge/Python-3.x-3776AB?logo=python&logoColor=white)](https://github.com/topics/python)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.x-009688?logo=fastapi&logoColor=white)](https://github.com/topics/fastapi)
[![WebSockets](https://img.shields.io/badge/WebSockets-Real--Time-4353FF)](https://github.com/topics/websocket)
[![CRDT](https://img.shields.io/badge/CRDT-Deterministic%20Merge-000000)](https://github.com/topics/crdt)
[![Distributed Systems](https://img.shields.io/badge/Distributed%20Systems-Correctness--First-2F3136)](https://github.com/topics/distributed-systems)
[![Testing](https://img.shields.io/badge/pytest-Test%20Suite-0A9EDC?logo=pytest&logoColor=white)](https://github.com/topics/pytest)
[![Docs](https://img.shields.io/badge/Docs-Architecture%20%26%20Protocol-4B5563)](https://github.com/topics/documentation)
[![Postgres (Phase 2)](https://img.shields.io/badge/PostgreSQL-Phase%202%20Plan-4169E1?logo=postgresql&logoColor=white)](https://github.com/topics/postgresql)
[![Real-Time Collaboration](https://img.shields.io/badge/Real--Time-Collaboration-111827)](https://github.com/topics/real-time-collaboration)
[![Phase 1](https://img.shields.io/badge/Phase%201-Locked%20%26%20Tested-16A34A)](#)


Production-grade real-time collaboration engine (Google Docs–style core) built with Python + FastAPI.

## Architecture

Components:
- Collaboration Engine: CRDT core logic (sequence CRDT for text)
- Transport Layer: WebSocket-based real-time communication
- Session Management: connected clients, per-document rooms
- Persistence Layer: operation log + snapshots (Phase 1: in-memory implementation)
- API Layer: FastAPI

Data flow:
- Clients connect via WebSocket and send `hello`
- Server responds with `hello_ack` (and either snapshot or replay strategy)
- Clients send operations (`op`) optimistically applied locally
- Server integrates via CRDT, assigns `server_seq`, appends to op log, and broadcasts `op_echo` to all clients (including origin)

## CRDT

Phase 1 uses an RGA-style sequence CRDT:
- Inserts reference a `parent_id` (insert-after)
- Concurrent inserts after same parent are deterministically ordered by `(lamport, replica_id)`
- Deletes are tombstones

See `docs/crdt.md`.

## WebSocket Protocol

See `docs/protocol.md`.

## Running

Install:

```bash
pip install -r requirements.txt
```

Run:

```bash
uvicorn collab_engine.main:app --app-dir src --host 0.0.0.0 --port 8000
```

Health check:

- `GET /health`

WebSocket:

- `WS /ws`

## Notes

- Phase 1 persistence is in-memory; restarting the server clears state.
- TODO markers exist in code for Phase 2+ (Postgres, snapshots schedule, authz, presence/cursors, backpressure/flow control improvements).
