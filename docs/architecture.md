# Architecture (Phase 1)

## Text diagram

```text
Clients
  | WebSocket (hello, op)
  v
FastAPI WS Endpoint
  v
Session Manager (doc rooms)
  v
Document Service
  - authoritative server_seq assignment
  - CRDT integration
  - persistence append
  v
Persistence
  - op log
  - snapshots (optional)
```

## Invariants

- `server_seq` is monotonically increasing per document.
- Every accepted operation is appended to the op log with its `server_seq`.
- Convergence is guaranteed by CRDT rules even if operations arrive out of order.

## Recovery

- Reconnect includes `last_seen_server_seq`.
- Server either replays ops since that seq or sends a snapshot when replay is not possible/too large.
