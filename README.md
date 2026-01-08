# collab-engine

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
