# Enhanced etcd Test Drivers

## Overview

Two new drivers were added to the etcd test composer to validate critical etcd primitives under fault injection:

1. **`eventually_lease_ttl`** — Tests lease TTL correctness across nodes
2. **`anytime_watch_consistency`** — Tests watch event delivery and ordering

---

## Driver 1: Lease TTL Validation (Eventually)

### Test Flow

```
   etcd0              etcd1              etcd2
     │                  │                  │
     │  1. Create lease │                  │
     │     (TTL=10s)    │                  │
     │  2. Put key ─────┼──────────────────┤
     │     with lease   │                  │
     │                  │  3. Read key     │
     │                  │     (verify      │
     │                  │     value+lease) │
     │                  │                  │
     │        ══════ wait for TTL ══════   │
     │                  │                  │
     │                  │                  │  4. Read key
     │                  │                  │     (verify
     │                  │                  │     deleted)
```

### What It Does

Creates a lease with a 10-second TTL on a random node, attaches a key, reads from a different node to verify consistency, waits for expiry, and confirms the key was cleaned up on a third node.

### Assertions

| Assertion | Type | Rationale |
|---|---|---|
| Lease creation succeeds | `sometimes` | Must work at least once; faults may cause failures |
| Leased key value corrupted across nodes | `unreachable` | A value mismatch is data corruption — must never happen |
| Leased key value is consistent across nodes | `always_or_unreachable` | If readable, value must match |
| Lease ID is consistent across nodes | `always_or_unreachable` | Lease metadata must replicate correctly |
| Key is removed after lease expiry | `always_or_unreachable` | Expired leases must clean up keys |
| Lease expiry cleans up keys | `sometimes` | Cleanup should work at least once |
| Lease TTL validation completed end-to-end | `reachable` | Confirms the full test path executes |

---

## Driver 2: Watch Event Consistency (Anytime)

### Test Flow

```
   Writer Node              Watcher Node
       │                        │
       │  1. Put initial key    │
       │                        │  2. Start watch
       │                        │     on key
       │  3. Put update-0  ────►│  ── event 0
       │  4. Put update-1  ────►│  ── event 1
       │  5. Put update-2  ────►│  ── event 2
       │  6. Put update-3  ────►│  ── event 3
       │  7. Put update-4  ────►│  ── event 4
       │                        │
       │           ═══ wait ═══ │
       │                        │
       │                        │  8. Verify:
       │                        │     - count matches
       │                        │     - order correct
       │                        │     - values match
       │                        │  9. Cancel watch
```

### What It Does

Writes to a key from one node while watching it from another. After a collection window, verifies that all events arrived, in correct order, with correct values. Runs as an **anytime** command so it executes repeatedly throughout testing, maximizing chances of catching intermittent issues.

### Assertions

| Assertion | Type | Rationale |
|---|---|---|
| Watch established successfully | `sometimes` | Watch setup should work at least once |
| Watch received more events than writes | `unreachable` | Duplicate events = a serious bug |
| Watch event values match written values | `always_or_unreachable` | Events must carry correct data |
| Watch events arrive in correct order | `always_or_unreachable` | etcd guarantees ordered delivery |
| All watch events received | `sometimes` | No event loss, at least once |
| Watch consistency test completed end-to-end | `reachable` | Confirms the full test path executes |

---

## Expected Bugs Under Fault Injection

These are specific failure modes I'd expect to surface when running in Antithesis with fault injection:

### Lease-Related Bugs

| Scenario | Fault | Expected Bug |
|---|---|---|
| Lease keepalive blocked | Network partition between client and leader | Key expires prematurely even though the client believes the lease is active. Could cause premature leader handoff in systems using lease-based election. |
| Leader crash during lease grant | Node crash | Lease granted on old leader may not replicate to new leader. Key appears to have a lease on some nodes but not others. |
| Partition during TTL expiry | Network partition between followers | Key exists on one side of the partition and is deleted on the other. After partition heals, the key state may be inconsistent. |
| Clock skew under faults | Slow I/O / process pause | TTL measured differently across nodes — key expires at different times on different nodes. |

### Watch-Related Bugs

| Scenario | Fault | Expected Bug |
|---|---|---|
| Leader election during watch | Leader crash | Watch stream may miss events that occurred during the leader transition. Client receives a gap in the event sequence. |
| Reconnect after partition | Network partition + heal | After reconnecting, the watch may replay events (duplicates) or skip events that occurred during the partition. |
| High write load + partition | Network partition | Watch events may arrive out of order if the watch stream is interrupted and re-established against a different node. |
| Watch on follower during split | Network partition | Follower falls behind on log replication; watch delivers stale or missing events until the follower catches up. |

---

## Why These Tests Matter

Real systems use etcd leases for **leader election** (Kubernetes, distributed locks) and watches for **configuration propagation** (service discovery, config management). Bugs in these primitives under network faults can cause:

- **Split-brain**: Two leaders simultaneously active
- **Stale config**: Services running on outdated configuration
- **Resource leaks**: Locks never released, sessions never cleaned up
- **Silent data loss**: Events dropped without notification

By testing both mechanisms across different nodes with varied assertion types, I maximize coverage of the most critical — and hardest to reproduce — failure modes in distributed etcd deployments.
