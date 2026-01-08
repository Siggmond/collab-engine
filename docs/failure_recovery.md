# Failure Scenarios and Recovery (Phase 1)

## Client reconnect

Client sends `hello` with `last_seen_server_seq`.

Server strategies:
- If op log has coverage since that seq, server replays `op_echo` messages.
- Otherwise server sends `resync` with a full snapshot.

## Slow consumer

Phase 1 uses a bounded per-connection send queue.

- If the queue overflows, the server closes the connection.

## Server restart

- In-memory persistence means document state is lost.
- Postgres persistence (Phase 2) will restore from snapshot + op log.
