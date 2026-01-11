# Phase 2: Tombstone GC & Compaction (Design Proposal)

**Status:** Planned  
**Phase 1:** Frozen (no behavioral changes)  
**Applies to:** Collab-Engine – RGA-based documents  
**Audience:** Contributors, reviewers, distributed-systems engineers  

This document proposes the **Phase 2 compaction strategy** for Collab-Engine.
Phase 1 behavior remains unchanged and is considered stable.

---

## Motivation

The current RGA implementation relies on **tombstones** to represent deletions.
While this guarantees correctness under concurrency, tombstones grow
**unbounded over time**, leading to:

- Increased memory footprint
- Larger snapshot sizes
- Higher replay and recovery CPU cost

Phase 2 introduces **controlled compaction** to reclaim space while preserving
correctness under real-world distributed conditions.

---

## Safety Model

The system must remain correct under the following assumptions:

- Messages may arrive **out of order**
- Clients may operate **offline** and reconnect later
- Old identifiers may be referenced long after their creation

Compaction must therefore define:

- Which identifiers remain valid
- When old references are rejected
- When a client resynchronization is required

Correctness takes priority over aggressive reclamation.

---

## Compaction Strategies

Two compaction levels are defined, with increasing effectiveness and risk.

---

## Level A: Conservative Pruning (No Epoch Change)

### Description

Physically remove tombstones **only when it is provably safe**, without
invalidating any existing identifiers.

This level does **not** introduce protocol-level changes.

### Safety Conditions (Potential)

A tombstone may be removed only if:

- The tombstoned node is a **leaf** (no children)
- The node is considered **stable** with respect to all clients that may later
  reference it

Stability implies that no future operation can legally reference the identifier.

### Risks

- If stability is miscomputed, a client may reference a removed identifier

### Mitigation

- Treat unresolved references as protocol violations
- Force client **resynchronization** when such references are detected

### Notes

This level prioritizes safety over space efficiency and may yield limited
reclamation in practice.

---

## Level B: Epoch-Based Compaction (Effective Reclamation)

### Description

Aggressively compact document state by explicitly **invalidating old identifiers**
using a document-level epoch mechanism.

This strategy enables substantial space reclamation at the cost of stricter
protocol rules.

### Mechanism

- Build a compacted snapshot of document state
- Increment `documents.epoch`
- Require clients to include `epoch` in all operations

### Client Behavior

- If client epoch matches document epoch: operations proceed normally
- If client epoch mismatches:
  - Reject operation
  - Force client resynchronization

### Properties

- Old identifiers are explicitly invalidated
- Safety is enforced via protocol-level versioning
- Correctness is preserved by construction

---

## Failure Modes & Handling

### Client References a GC’d Identifier

- **Level A (Conservative):**
  - Should not occur if stability is computed correctly
  - If detected, force resync

- **Level B (Epoch-Based):**
  - Expected on epoch mismatch
  - Force resync and reject operation

---

### Partial Compaction Persisted

- Compaction must be **transactional**
- Partial state persistence is not allowed
- System must guarantee atomic visibility of compaction results

---

### Compaction Concurrent with Operations

- Compaction must execute under a **per-document lock**
- Operations must either:
  - Observe the pre-compaction state, or
  - Observe the fully compacted state
- No mixed visibility is allowed

---

## Summary

Phase 2 introduces structured compaction while maintaining the core correctness
guarantees of the RGA model.

- Level A offers conservative, low-risk pruning
- Level B provides effective reclamation with explicit protocol enforcement

The choice of strategy can be implementation-dependent and may evolve over time.

This document defines **design intent only**; implementation details may vary.
