# Text CRDT – Phase 1 (RGA-Style Sequence CRDT)

**Status:** Implemented (Frozen)  
**Scope:** Text sequence representation and convergence rules  
**Applies to:** Collab-Engine collaborative documents  
**Audience:** Contributors, CRDT practitioners, system reviewers  

This document describes the **Phase 1 text CRDT model** used by Collab-Engine.
Phase 1 behavior is considered stable and serves as the correctness baseline
for future optimizations.

---

## Overview

Collab-Engine uses an **RGA-style (Replicated Growable Array)** sequence CRDT
to represent collaboratively edited text.

The model guarantees **strong eventual consistency** under:
- Concurrent inserts
- Out-of-order delivery
- Client disconnects and reconnections

---

## Data Model

Each inserted element in the sequence is represented as a node with the
following fields:

- `id`
  - Tuple: `(lamport: int, replica_id: str)`
  - Uniquely identifies the element
- `parent_id`
  - Identifier of the element **after which** this element was inserted
- `value`
  - Text payload
  - Phase 1 restricts this to **single-character inserts**
- `deleted`
  - Boolean tombstone flag indicating logical deletion

Elements are never physically removed in Phase 1.

---

## Operations

### Insert

- Semantics: **insert-after**
- Operation references a `parent_id`
- A new element with a fresh `id` is created and inserted into the sequence

---

### Delete

- Semantics: **logical deletion**
- Operation references an element `id`
- The referenced element is marked as `deleted`
- Deleted elements remain in the structure as tombstones

---

## Deterministic Ordering

When multiple inserts reference the same `parent_id`, their relative order is
determined by a **total ordering on element identifiers**:

(lamport, replica_id) // lexicographic ordering

yaml
Copy code

This ensures that all replicas converge on the same sequence order regardless
of message delivery order.

---

## Dependency Handling

Operations may arrive before their dependencies due to network reordering or
offline clients.

The system handles this by:

- Buffering inserts that reference **unknown `parent_id`s**
- Buffering deletes that reference **unknown element `id`s**
- Applying buffered operations once dependencies are satisfied

This buffering preserves correctness without rejecting valid operations.

---

## Trade-offs & Limitations

Phase 1 intentionally prioritizes **simplicity and correctness**.

Known trade-offs include:

- **Tombstone accumulation**
  - Deleted elements are never physically removed
  - Addressed in Phase 2+ compaction designs
- **Single-character inserts**
  - Simplifies CRDT logic
  - Not optimal for performance or storage
  - Chunking and batching are deferred to later phases

These limitations are deliberate and documented design decisions.

---

## Design Rationale

The Phase 1 CRDT design favors:

- Deterministic convergence
- Explicit dependency handling
- Minimal assumptions about client behavior

This provides a solid foundation for future enhancements without risking
correctness regressions.

---

## Notes

- Phase 1 CRDT behavior is frozen
- Any optimization must either:
  - Preserve these semantics, or
  - Introduce explicit versioning
- This document defines the **authoritative text model** for the system
