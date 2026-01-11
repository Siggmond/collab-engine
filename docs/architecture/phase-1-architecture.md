# Architecture – Phase 1 (Authoritative Server, CRDT-Based Sync)

**Status:** Implemented (Frozen)  
**Scope:** Core real-time synchronization path  
**Applies to:** Collab-Engine document sessions  
**Audience:** Contributors, system designers, reviewers  

This document describes the **Phase 1 architecture** of Collab-Engine.
Phase 1 defines the baseline, stable behavior of the system and is treated as
authoritative for correctness guarantees.

---

## High-Level Overview

Phase 1 implements a **server-authoritative real-time collaboration system**
built on top of:

- WebSockets for bidirectional communication
- An authoritative server sequence (`server_seq`)
- CRDT-based convergence for out-of-order operations
- Append-only persistence for recovery and replay

The server acts as the source of truth for operation ordering while allowing
clients to operate concurrently and reconnect safely.

---

## Data Flow (Text Diagram)

Clients
|
| WebSocket (hello, op)
v
FastAPI WebSocket Endpoint
|
v
Session Manager (Document Rooms)
|
v
Document Service

Authoritative server_seq assignment

CRDT integration

Persistence append
|
v
Persistence Layer

Operation log (append-only)

Snapshots (optional)

yaml
Copy code

---

## Core Components

### Clients
- Establish a WebSocket connection
- Send:
  - `hello` messages (session initialization)
  - document operations (`op`)
- Track the last acknowledged `server_seq`

---

### FastAPI WebSocket Endpoint
- Terminates WebSocket connections
- Performs protocol-level validation
- Routes messages to the appropriate document session

---

### Session Manager
- Maintains **document rooms**
- Tracks connected clients per document
- Broadcasts accepted operations to all participants

---

### Document Service
The core authoritative component.

Responsibilities:
- Assign a **monotonically increasing `server_seq`** per document
- Apply operations to the CRDT
- Append accepted operations to persistence
- Enforce invariants before broadcast

---

### Persistence Layer
- Append-only **operation log**
- Optional **snapshots** for fast recovery
- Provides durability and replay guarantees

---

## System Invariants

The following invariants **must always hold**:

1. `server_seq` is **monotonically increasing** per document
2. Every accepted operation:
   - Is assigned a `server_seq`
   - Is appended to the operation log
3. All clients eventually observe operations in `server_seq` order
4. Convergence is guaranteed by CRDT rules, even if:
   - Operations arrive out of order
   - Clients reconnect after being offline

Violating any of these invariants is considered a correctness failure.

---

## Recovery & Reconnection Model

### Client Reconnection

On reconnect, the client sends:
- `last_seen_server_seq`

### Server Behavior

The server evaluates recovery strategy:

- If the operation log contains all ops after `last_seen_server_seq`:
  - Replay missing operations
- If replay is not possible or exceeds limits:
  - Send a snapshot
  - Resume normal operation after snapshot application

This ensures:
- No accepted operation is lost
- Clients always converge to the authoritative state

---

## Design Rationale

Phase 1 intentionally prioritizes:

- **Correctness over optimization**
- **Explicit ordering over implicit assumptions**
- **Recoverability over minimal state**

This foundation enables later phases (e.g. compaction, epochs) without
weakening correctness guarantees.

---

## Notes

- Phase 1 behavior is frozen and treated as stable
- Future phases must preserve these invariants or explicitly version them
- This document describes the **authoritative execution path**
