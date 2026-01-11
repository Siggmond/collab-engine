# WebSocket Protocol – Phase 1

**Status:** Implemented (Frozen)  
**Scope:** Client–server messaging over WebSockets  
**Applies to:** Collab-Engine real-time document sessions  
**Audience:** Contributors, client implementers, reviewers  

This document specifies the **Phase 1 WebSocket protocol** used by
Collab-Engine. Phase 1 behavior is frozen and defines the authoritative
messaging contract between clients and the server.

All messages are encoded as **JSON objects** and include a top-level `type`
field.

---

## General Conventions

- All messages include a `type` field
- Clients may send operations optimistically
- The server assigns the authoritative `server_seq`
- Clients must tolerate receiving their own operations back from the server

---

## Client → Server Messages

### `hello`

Sent by a client when establishing or re-establishing a session.

```json
{
  "type": "hello",
  "doc_id": "doc-123",
  "client_id": "client-A",
  "last_seen_server_seq": 42
}
```

**Semantics:**
- Identifies the document and client
- Communicates the last operation acknowledged by the client
- Allows the server to choose replay vs resync

---

### `op` (Insert)

```json
{
  "type": "op",
  "doc_id": "doc-123",
  "client_id": "client-A",
  "client_msg_id": "uuid-or-monotonic",
  "op": {
    "type": "ins",
    "parent_id": [0, "root"],
    "id": [1001, "client-A"],
    "value": "H"
  }
}
```

**Semantics:**
- Submits a CRDT insert operation
- `client_msg_id` is used for idempotency
- `id` must be globally unique per element

---

### `op` (Delete)

```json
{
  "type": "op",
  "doc_id": "doc-123",
  "client_id": "client-A",
  "client_msg_id": "...",
  "op": {
    "type": "del",
    "id": [1001, "client-A"]
  }
}
```

**Semantics:**
- Marks the referenced element as deleted (tombstone)
- Physical removal is deferred to later phases

---

## Server → Client Messages

### `hello_ack`

Sent in response to `hello`.

```json
{
  "type": "hello_ack",
  "doc_id": "doc-123",
  "server_seq": 42,
  "full_text": "..."
}
```

**Semantics:**
- Confirms successful session establishment
- Communicates the current authoritative sequence
- May include an initial snapshot of document state

---

### `op_echo`

Broadcast by the server for every accepted operation.

```json
{
  "type": "op_echo",
  "doc_id": "doc-123",
  "server_seq": 43,
  "origin_client_id": "client-A",
  "client_msg_id": "...",
  "op": {
    "type": "ins",
    "parent_id": [0, "root"],
    "id": [1001, "client-A"],
    "value": "H"
  }
}
```

**Semantics:**
- Represents an operation committed by the server
- Delivered to all clients, including the originator
- `server_seq` defines the canonical ordering

---

### `resync`

Sent when incremental replay is not possible or safe.

```json
{
  "type": "resync",
  "doc_id": "doc-123",
  "server_seq": 100,
  "full_text": "..."
}
```

**Semantics:**
- Instructs the client to replace local state
- Establishes a new synchronization baseline
- Client resumes normal operation after applying snapshot

---

## Protocol Guarantees

- All accepted operations receive a unique `server_seq`
- Clients converge by applying operations in `server_seq` order
- Correctness does not depend on message delivery order
- Resynchronization is always safe when replay cannot be guaranteed

---

## Notes

- This protocol defines Phase 1 behavior only
- Future phases may extend messages but must not break compatibility
- Any deviation from this contract is a correctness violation
