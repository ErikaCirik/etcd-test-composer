#!/usr/bin/env -S python3 -u
# -S flag lets env split the arguments; -u forces unbuffered output so prints appear immediately

import sys
import time

# Add the shared resources folder to Python's module search path so we can import helper.py
sys.path.append("/opt/antithesis/resources")
import helper  # helper.py provides connect_to_host(), generate_random_string(), put/get wrappers

# Import all the Antithesis assertion types we use in this test
from antithesis.assertions import (
    always,               # condition must be true every time (not used here, but available)
    sometimes,            # condition must be true at least once across all runs
    always_or_unreachable,  # if this line runs, condition must be true; OK if never reached
    unreachable,          # this line should NEVER execute; if it does, it's a critical bug
    reachable,            # this line MUST execute at least once; proves the test completed
)

# The lease will expire after 10 seconds
LEASE_TTL = 10


def test_lease_ttl():
    print("Client [lease-ttl]: starting lease TTL validation...")

    # STEP 1: Connect to a random etcd node (etcd0, etcd1, or etcd2)
    # helper.connect_to_host() uses Antithesis randomness to pick a node
    client1 = helper.connect_to_host()

    # STEP 2: Create a lease with a 10-second TTL
    lease = None
    try:
        lease = client1.lease(LEASE_TTL)  # Ask etcd for a lease that expires in 10 seconds
        print(f"Client [lease-ttl]: created lease with ID {lease.id} and TTL {LEASE_TTL}s")
    except Exception as e:
        # If lease creation fails (e.g., due to a fault), record it with sometimes(False)
        # This won't fail the test — it just records that this attempt didn't work
        sometimes(False, "Lease creation succeeds", {"error": str(e)})
        print(f"Client [lease-ttl]: failed to create lease: {e}")
        return  # Can't continue without a lease

    # Record that lease creation succeeded — "sometimes" means at least one run must succeed
    sometimes(True, "Lease creation succeeds", {"lease_id": lease.id})

    # STEP 3: Generate a random key and value, then store them with the lease attached
    key = "lease-test-" + helper.generate_random_string()    # e.g., "lease-test-HM2LAd8F"
    value = "val-" + helper.generate_random_string()          # e.g., "val-YTKM1ug5"

    try:
        # Put the key-value pair into etcd, attached to our lease
        # When the lease expires, this key will be automatically deleted
        client1.put(key, value, lease=lease)
        print(f"Client [lease-ttl]: attached key '{key}' to lease {lease.id}")
    except Exception as e:
        print(f"Client [lease-ttl]: failed to put key with lease: {e}")
        return  # Can't verify if the put didn't work
    finally:
        client1.close()  # Always close the connection when done

    # STEP 4: Read the key from a DIFFERENT random node to test cross-node consistency
    # This is the core value of the test — data must replicate correctly
    client2 = helper.connect_to_host()  # Connects to a random node (may differ from client1)
    try:
        result, metadata = client2.get(key)  # Read the key from a different node
        if result is not None:
            retrieved = result.decode("utf-8")  # Convert bytes to string
            key_matches = retrieved == value     # Does the value match what we wrote?

            # If values don't match, this is DATA CORRUPTION — should never happen
            if not key_matches:
                unreachable(
                    "Leased key value corrupted across nodes",
                    {"expected": value, "got": retrieved},
                )

            # If we reached this line and can read the key, the value must be correct
            always_or_unreachable(
                key_matches,
                "Leased key value is consistent across nodes",
                {"expected": value, "got": retrieved},
            )
            print(f"Client [lease-ttl]: verified key '{key}' on different node, value matches: {key_matches}")

            # Also verify the lease ID is the same across nodes
            if metadata and metadata.lease_id:
                lease_id_matches = metadata.lease_id == lease.id
                always_or_unreachable(
                    lease_id_matches,
                    "Lease ID is consistent across nodes",
                    {"expected": lease.id, "got": metadata.lease_id},
                )
                print(f"Client [lease-ttl]: lease ID matches across nodes: {lease_id_matches}")
        else:
            # Key not found — possible if a fault disrupted replication
            # This is OK, the always_or_unreachable above simply won't fire
            print(f"Client [lease-ttl]: key '{key}' not found on second node (possible fault)")
    except Exception as e:
        print(f"Client [lease-ttl]: failed to get key from second node: {e}")
    finally:
        client2.close()

    # STEP 5: Wait for the lease to expire (TTL + 5 second buffer for clock variance)
    wait_time = LEASE_TTL + 5  # 10 + 5 = 15 seconds
    print(f"Client [lease-ttl]: waiting {wait_time}s for lease to expire...")
    time.sleep(wait_time)

    # STEP 6: Verify the key was automatically deleted after lease expiry
    # Connect to yet another random node for this check
    client3 = helper.connect_to_host()
    try:
        result, _ = client3.get(key)  # Try to read the key again
        key_expired = result is None  # Key should be gone (None = not found)

        # If we can check, the key MUST be gone — a lingering key is a bug
        always_or_unreachable(
            key_expired,
            "Key is removed after lease expiry",
            {"key": key, "value_found": result},
        )
        # Record that cleanup worked — must succeed at least once
        sometimes(key_expired, "Lease expiry cleans up keys", {"key": key})
        print(f"Client [lease-ttl]: key expired correctly: {key_expired}")
    except Exception as e:
        print(f"Client [lease-ttl]: failed to verify key expiry: {e}")
    finally:
        client3.close()

    # STEP 7: Mark that the test ran all the way to completion
    # If the test crashes or exits early, this assertion won't fire → test fails
    reachable("Lease TTL validation completed end-to-end", {})
    print("Client [lease-ttl]: lease TTL validation complete!")
    time.sleep(1)  # Brief pause to let the SDK flush output to the file


# Standard Python entry point — runs the test when executed directly
if __name__ == "__main__":
    test_lease_ttl()
