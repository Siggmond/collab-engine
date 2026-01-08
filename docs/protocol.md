# WebSocket Protocol (Phase 1)

All messages are JSON objects with a `type` field.

## Client -> Server

### `hello`

```json
{
  "type": "hello",
  "doc_id": "doc-123",
  "client_id": "client-A",
  "last_seen_server_seq": 42
}
```

### `op`

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

Delete:

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

## Server -> Client

### `hello_ack`

```json
{
  "type": "hello_ack",
  "doc_id": "doc-123",
  "server_seq": 42,
  "full_text": "..."
}
```

### `op_echo`

```json
{
  "type": "op_echo",
  "doc_id": "doc-123",
  "server_seq": 43,
  "origin_client_id": "client-A",
  "client_msg_id": "...",
  "op": { "type": "ins", "parent_id": [0,"root"], "id": [1001,"client-A"], "value": "H" }
}
```

### `resync`

```json
{
  "type": "resync",
  "doc_id": "doc-123",
  "server_seq": 100,
  "full_text": "..."
}
```
