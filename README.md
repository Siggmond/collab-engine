# collab-engine

collab-engine is a correctness-focused real-time collaboration backend: the core backend idea behind a Google Docs-style shared text editor, implemented with Python, FastAPI, WebSockets, and a deterministic text CRDT.

Phase 1 is an in-memory reference implementation designed for portfolio review and technical evaluation. It demonstrates protocol semantics, replay/resync behavior, and CRDT correctness boundaries; it is not a full production collaboration platform.

## Quick Reviewer Path

If you have five minutes, start here:

1. Understand the problem: collab-engine accepts WebSocket clients editing the same document, assigns authoritative server ordering, integrates edits through a deterministic text CRDT, broadcasts canonical operation echoes, and helps reconnecting clients recover with replay or snapshot resync.
2. Confirm Phase 1 scope: the implemented system includes the FastAPI WebSocket endpoint, per-document rooms, strict `hello` / `hello_ack` handshake, in-memory op log and snapshots, server-assigned `server_seq`, RGA-style insert/delete behavior, replay-on-reconnect, and snapshot resync fallback.
3. Inspect the key code and docs:

| Topic | Where to look |
| --- | --- |
| CRDT logic | [`src/collab_engine/core/crdt/rga.py`](src/collab_engine/core/crdt/rga.py), [`docs/crdt/phase-1-text-crdt.md`](docs/crdt/phase-1-text-crdt.md) |
| WebSocket protocol | [`src/collab_engine/api/ws.py`](src/collab_engine/api/ws.py), [`src/collab_engine/core/protocol/messages.py`](src/collab_engine/core/protocol/messages.py), [`docs/protocol/phase-1-websocket-protocol.md`](docs/protocol/phase-1-websocket-protocol.md) |
| Server sequencing and snapshots | [`src/collab_engine/services/document_service.py`](src/collab_engine/services/document_service.py), [`src/collab_engine/persistence/memory.py`](src/collab_engine/persistence/memory.py) |
| Replay/resync behavior | [`docs/reliability/phase-1-failure-recovery.md`](docs/reliability/phase-1-failure-recovery.md), [`src/collab_engine/api/ws.py`](src/collab_engine/api/ws.py) |
| Correctness tests | [`tests/test_rga.py`](tests/test_rga.py), [`tests/test_snapshot_replay.py`](tests/test_snapshot_replay.py) |
| Phase 2 boundary | [`docs/plan/phase-2-design-plan.md`](docs/plan/phase-2-design-plan.md), [`docs/persistence/phase-2-persistence.md`](docs/persistence/phase-2-persistence.md), [`docs/design/phase2_compaction.md`](docs/design/phase2_compaction.md), [`docs/presence/phase-2-presence.md`](docs/presence/phase-2-presence.md) |

Run the server:

```bash
pip install -r requirements.txt
uvicorn collab_engine.main:app --app-dir src --host 0.0.0.0 --port 8000
```

Run tests:

```bash
pip install -r requirements-dev.txt
pytest
```

The protocol examples in [`docs/protocol/phase-1-websocket-protocol.md`](docs/protocol/phase-1-websocket-protocol.md) show the JSON contract for client hello, operations, server acknowledgements, operation echo, and resync. The screenshots in [`docs/screenshots/`](docs/screenshots/) show the server, health/API surface, WebSocket handshake, multi-client behavior, concurrent inserts, replay, and resync flows.

## What This Project Proves

- Real-time backend architecture with FastAPI and WebSockets.
- Deterministic text CRDT behavior using an RGA-style sequence model.
- Safe handling of concurrent inserts by ordering same-parent children with `(lamport, replica_id)`.
- Tombstone-based deletes that preserve references needed by later operations.
- Authoritative server sequencing with monotonic per-document `server_seq`.
- Replay-on-reconnect using `last_seen_server_seq`.
- Snapshot resync fallback when replay is not available or not appropriate.
- Protocol design with a strict first-message `hello` and server `hello_ack`.
- Correctness-focused automated tests for CRDT determinism, dependency buffering, tombstones, idempotent replay, and snapshot/replay consistency.
- Honest separation between implemented Phase 1 behavior and design-only Phase 2 plans.

## Phase 1 vs Phase 2

| Phase | Status | Scope |
| --- | --- | --- |
| Phase 1 | Implemented, tested, frozen/locked | In-memory FastAPI/WebSocket collaboration backend, deterministic RGA-style text CRDT, per-document rooms, authoritative sequencing, in-memory op log/snapshot storage, replay/resync behavior, and core correctness tests. |
| Phase 2 | Docs/design only, not implemented | Durable PostgreSQL persistence, tombstone compaction, presence/cursors, auth/authorization boundary, deeper observability, and scaling strategy proposals. |

Reviewers should treat Phase 1 as the executable reference implementation and Phase 2 as architecture planning. Phase 2 documents are intentionally present to show forward design thinking, not to claim runtime support.

## Architecture

Components:

- Collaboration Engine: deterministic RGA-style sequence CRDT for plain text.
- Transport Layer: WebSocket-based real-time communication.
- Session Management: connected clients and per-document rooms.
- Persistence Layer: in-memory operation log and latest text snapshot for Phase 1.
- API Layer: FastAPI health endpoint and WebSocket endpoint.

Data flow:

1. Client connects to `WS /ws` and sends `hello`.
2. Server validates that `hello` is the first message and responds with `hello_ack`.
3. Server sends either replayed `op_echo` messages or a `resync` snapshot.
4. Client sends `op` messages.
5. Server integrates each operation through the CRDT, assigns `server_seq`, appends to the in-memory op log, updates the snapshot text, and broadcasts `op_echo` to all clients in the document room, including the origin client.

## CRDT Model

Phase 1 uses an RGA-style sequence CRDT:

- Inserts reference a `parent_id` using insert-after semantics.
- Concurrent inserts after the same parent are deterministically ordered by `(lamport, replica_id)`.
- Deletes are tombstones, so removed elements remain addressable for later dependent operations.
- Inserts and deletes that arrive before their dependencies are buffered until the dependency exists.

See [`docs/crdt/phase-1-text-crdt.md`](docs/crdt/phase-1-text-crdt.md) and [`tests/test_rga.py`](tests/test_rga.py).

## WebSocket Protocol

The WebSocket protocol is intentionally small:

- Client to server: `hello`, then `op`.
- Server to client: `hello_ack`, `op_echo`, and `resync`.
- The first client message must be `hello`; invalid or out-of-order messages are closed as protocol violations.
- Clients may apply operations optimistically, but the server echo is the authoritative sequenced record.

See [`docs/protocol/phase-1-websocket-protocol.md`](docs/protocol/phase-1-websocket-protocol.md) and [`docs/reliability/phase-1-failure-recovery.md`](docs/reliability/phase-1-failure-recovery.md).

## Screenshots and Protocol Evidence

These assets are optional reviewer evidence, not required to run the project:

| Evidence | What it shows |
| --- | --- |
| [`docs/screenshots/01-server-running.png`](docs/screenshots/01-server-running.png) | Uvicorn server running locally. |
| [`docs/screenshots/02-health.png`](docs/screenshots/02-health.png) | Health endpoint response. |
| [`docs/screenshots/03-swagger.png`](docs/screenshots/03-swagger.png) | FastAPI API documentation surface. |
| [`docs/screenshots/04-ws-handshake.png`](docs/screenshots/04-ws-handshake.png) | WebSocket `hello` / `hello_ack` handshake and initial sync path. |
| [`docs/screenshots/05-two-clients.png`](docs/screenshots/05-two-clients.png) | Two clients sharing a document room. |
| [`docs/screenshots/06-concurrent-inserts.jpeg`](docs/screenshots/06-concurrent-inserts.jpeg) | Concurrent insert behavior under deterministic CRDT ordering. |
| [`docs/screenshots/07-replay.jpeg`](docs/screenshots/07-replay.jpeg) | Reconnect replay behavior. |
| [`docs/screenshots/08-resync.png`](docs/screenshots/08-resync.png) | Snapshot resync fallback behavior. |

## Running

Install runtime dependencies:

```bash
pip install -r requirements.txt
```

Run the server:

```bash
uvicorn collab_engine.main:app --app-dir src --host 0.0.0.0 --port 8000
```

Useful endpoints:

- `GET /health`
- `WS /ws`

## Tests

Install test dependency:

```bash
pip install -r requirements-dev.txt
```

Run the available test suite:

```bash
pytest
```

The tests focus on CRDT correctness and replay/snapshot consistency rather than UI behavior because this repository does not include a frontend.

## Current Scope / Honest Limitations

- Phase 1 persistence is in-memory.
- Restarting the server clears document state.
- There is no UI; this is backend/protocol work only.
- Auth and authorization are Phase 2 design boundaries, not implemented production controls.
- Phase 2 is design-only unless code is explicitly added later.
- Production use would require durable persistence, authentication and authorization, rate limiting, a horizontal scaling strategy, observability, stronger backpressure handling, deployment hardening, and operational testing.

## Documentation Map

- [`docs/architecture/phase-1-architecture.md`](docs/architecture/phase-1-architecture.md): Phase 1 architecture and invariants.
- [`docs/crdt/phase-1-text-crdt.md`](docs/crdt/phase-1-text-crdt.md): RGA-style text CRDT model and trade-offs.
- [`docs/protocol/phase-1-websocket-protocol.md`](docs/protocol/phase-1-websocket-protocol.md): WebSocket message contract.
- [`docs/reliability/phase-1-failure-recovery.md`](docs/reliability/phase-1-failure-recovery.md): reconnect replay, resync, slow-consumer, and restart behavior.
- [`docs/plan/phase-2-design-plan.md`](docs/plan/phase-2-design-plan.md): Phase 2 design plan and boundaries.
- [`docs/persistence/phase-2-persistence.md`](docs/persistence/phase-2-persistence.md): proposed PostgreSQL persistence model.
- [`docs/design/phase2_compaction.md`](docs/design/phase2_compaction.md): proposed tombstone compaction strategy.
- [`docs/presence/phase-2-presence.md`](docs/presence/phase-2-presence.md): proposed presence/cursor model.

## License

MIT
