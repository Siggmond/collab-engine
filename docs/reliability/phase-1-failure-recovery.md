# Failure Scenarios & Recovery – Phase 1

**Status:** Implemented (Frozen)  
**Scope:** Client recovery, backpressure handling, server restarts  
**Applies to:** Collab-Engine real-time document sessions  
**Audience:** Contributors, system designers, reviewers  

This document describes how **Phase 1** of Collab-Engine handles common failure
scenarios while preserving correctness and convergence guarantees.

Phase 1 behavior is considered stable and serves as the baseline for future
durability improvements.

---

## Overview

Phase 1 focuses on **correctness-first recovery** under realistic failure modes:

- Client disconnects and reconnects
- Slow or stalled consumers
- Server restarts without durable persistence

The system prioritizes:
- Deterministic recovery
- Explicit resynchronization when safety cannot be guaranteed
- Clear failure boundaries

---

## Client Reconnection

### Scenario

A client disconnects (network loss, app restart, offline operation) and later
reconnects to the server.

### Client Behavior

On reconnect, the client sends a `hello` message containing:

- `last_seen_server_seq`

This value represents the last operation the client successfully applied.

---

### Server Recovery Strategy

Upon receiving the reconnect request, the server chooses one of two strategies:

#### 1. Incremental Replay

If the operation log contains **full coverage** since `last_seen_server_seq`:

- Replay all missing operations
- Send them as `op_echo` messages
- Resume normal real-time synchronization

This is the preferred and lowest-cost recovery path.

---

#### 2. Full Resynchronization

If replay is **not possible** (e.g. log truncated, too large, unavailable):

- Send a `resync` message
- Include a full document snapshot
- Client replaces local state with the snapshot
- Resume normal operation after sync

This guarantees correctness even when incremental replay cannot be used.

---

## Slow Consumer Handling

### Scenario

A connected client is unable to process incoming messages fast enough
(e.g. stalled UI thread, network congestion).

---

### Phase 1 Strategy

- Each connection maintains a **bounded send queue**
- Outgoing messages are enqueued per client

If the queue **overflows**:

- The server **closes the connection**
- The client is expected to reconnect and recover via replay or resync

---

### Rationale

- Prevents unbounded memory growth
- Avoids backpressure affecting other clients
- Keeps failure handling explicit and recoverable

This design treats slow consumers as transient failures rather than special
cases.

---

## Server Restart

### Scenario

The server process restarts (crash, redeploy, manual restart).

---

### Phase 1 Behavior

- Persistence is **in-memory**
- All document state is lost on restart
- Clients must reconnect and resynchronize

This limitation is intentional in Phase 1.

---

### Forward Compatibility (Phase 2+)

Planned persistence improvements include:

- Durable storage (e.g. PostgreSQL)
- Snapshot persistence
- Append-only operation logs

After restart, the server will restore state from:

1. Latest snapshot
2. Operation log replay

This enables transparent recovery without client-visible data loss.

---

## Design Rationale

Phase 1 explicitly favors:

- Clear failure boundaries
- Simple, predictable recovery paths
- Correctness over availability during failure

Rather than attempting partial recovery under uncertainty, the system opts for
**explicit resynchronization** when safety cannot be guaranteed.

---

## Notes

- All Phase 1 recovery behavior is frozen
- Future phases must preserve these guarantees or introduce explicit versioning
- This document defines the authoritative failure-handling model
