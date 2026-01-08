# Text CRDT (Phase 1): RGA-style sequence CRDT

## Model

Each inserted element has:
- `id`: `(lamport: int, replica_id: str)`
- `parent_id`: id of the element after which it was inserted
- `value`: string (Phase 1 uses single-character inserts)
- `deleted`: tombstone flag

## Operations

- Insert: insert-after semantics
- Delete: tombstone by element id

## Deterministic ordering

If multiple inserts reference the same `parent_id`, children are ordered by total ordering on `id`:
- `(lamport, replica_id)` lexicographic

## Dependency handling

Inserts referencing unknown parents and deletes referencing unknown ids are buffered until dependencies arrive.

## Trade-offs

- Tombstones accumulate; compaction is deferred to Phase 2+.
- Single-character inserts are simplest but not optimal; chunking is deferred.
