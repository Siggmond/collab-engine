# Phase 2: Tombstone GC / Compaction

## Phase 1 is frozen

This document proposes Phase 2 compaction strategy only. Phase 1 behavior remains unchanged.

---

## Why compaction is needed

RGA uses tombstones for deletion. Tombstones grow unbounded, which increases:
- memory footprint
- snapshot size
- replay CPU

---

## Safety model

Out-of-order delivery and offline clients mean old identifiers may be referenced later.
Compaction must define what references are still accepted and when resync is required.

---

## Compaction levels

### Level A: conservative pruning (no epoch change)

Physically remove tombstones only when provably safe without invalidating ids.

Potential safety conditions:
- tombstoned node is a leaf (no children)
- node is stable w.r.t. all clients that might later reference it

Risk:
- If stability is miscomputed, a client may reference a removed id.

Mitigation:
- Force resync on unresolved references.

### Level B: epoch-based compaction (effective reclamation)

Aggressively compact and explicitly invalidate old identifiers.

- Build compacted snapshot
- Increment `documents.epoch`
- Require epoch in client messages
- On epoch mismatch: resync + reject old-epoch ops

---

## Failure modes

- Client references a GC’d id:
  - conservative pruning: should not happen; otherwise resync
  - epoch compaction: expected on mismatch; resync

- Partial compaction persisted:
  - must be transactional

- Compaction races with ops:
  - run under per-document lock
