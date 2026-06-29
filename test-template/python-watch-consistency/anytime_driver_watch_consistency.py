#!/usr/bin/env -S python3 -u
# -S flag lets env split the arguments; -u forces unbuffered output so prints appear immediately

import sys
import time
import threading  # We run the watch listener in a separate thread so it doesn't block

# Add the shared resources folder so we can import helper.py
sys.path.append("/opt/antithesis/resources")
import helper  # Provides connect_to_host(), generate_random_string()

import etcd3  # The Python etcd client library — we use it directly here for watch support
from antithesis.random import random_choice  # Antithesis-aware random selection

# Import Antithesis assertion types
from antithesis.assertions import (
    always_or_unreachable,  # If this line runs, condition must always be true
    sometimes,              # Condition must be true at least once across all runs
    unreachable,            # This line should NEVER execute — critical bug if it does
    reachable,              # This line MUST execute at least once — proves test completed
)

NUM_UPDATES = 5    # How many times we update the key
WATCH_TIMEOUT = 15  # Max seconds to wait for watch events to arrive


def test_watch_consistency():
    print("Client [watch]: starting watch consistency test...")

    # STEP 1: Generate a unique key and initial value using Antithesis randomness
    key = "watch-test-" + helper.generate_random_string()      # e.g., "watch-test-m2eelo3z"
    initial_value = "init-" + helper.generate_random_string()   # e.g., "init-abc12345"

    # STEP 2: Create the key on a random etcd node (the "writer" node)
    host1 = random_choice(["etcd0", "etcd1", "etcd2"])  # Pick a random node to write to
    writer = etcd3.client(host=host1, port=2379)         # Connect to that node
    try:
        writer.put(key, initial_value)  # Create the key with an initial value
        print(f"Client [watch]: created key '{key}' on {host1}")
    except Exception as e:
        print(f"Client [watch]: failed to create initial key: {e}")
        writer.close()
        return  # Can't continue if we can't even create the key

    # STEP 3: Set up a watch on the key from a DIFFERENT random node
    # Watching from a different node tests that watch events propagate across the cluster
    host2 = random_choice(["etcd0", "etcd1", "etcd2"])  # Pick a (possibly different) node
    watcher = etcd3.client(host=host2, port=2379)        # Connect to that node for watching

    received_values = []  # List to collect values from watch events
    watch_error = [None]  # Using a list so the thread can modify it (mutable reference)

    # This function runs in a background thread — it listens for watch events
    def watch_thread_fn():
        try:
            # watcher.watch() returns an iterator of events and a cancel function
            events_iter, cancel = watcher.watch(key)
            for event in events_iter:  # Blocks until an event arrives
                # Each event has a .value attribute with the new value of the key
                if hasattr(event, 'value') and event.value is not None:
                    received_values.append(event.value.decode("utf-8"))  # Store the value
                    # Once we've received all expected events, cancel the watch
                    if len(received_values) >= NUM_UPDATES:
                        cancel()  # Stops the watch stream
                        break
        except Exception as e:
            watch_error[0] = e  # Record any error so the main thread can check

    # Start the watch listener in a background daemon thread
    # daemon=True means the thread dies automatically when the main program exits
    watch_thread = threading.Thread(target=watch_thread_fn, daemon=True)
    watch_thread.start()
    time.sleep(2)  # Give the watch 2 seconds to fully establish before we start writing

    # Check if the watch thread encountered an error during setup
    if watch_error[0]:
        sometimes(False, "Watch established successfully", {"error": str(watch_error[0])})
        print(f"Client [watch]: watch failed: {watch_error[0]}")
        writer.close()
        watcher.close()
        return

    # Record that the watch was established — must succeed at least once
    sometimes(True, "Watch established successfully", {"key": key, "writer": host1, "watcher": host2})
    print(f"Client [watch]: watch established on '{key}' via {host2}")

    # STEP 4: Write NUM_UPDATES (5) updates to the key from the writer node
    # The watcher on the other node should receive events for each update
    written_values = []  # Track what we wrote so we can verify later
    for i in range(NUM_UPDATES):
        value = f"update-{i}-" + helper.generate_random_string()  # e.g., "update-0-EpQRna8A"
        try:
            writer.put(key, value)  # Overwrite the key with a new value
            written_values.append(value)  # Remember this value for verification
            print(f"Client [watch]: wrote update {i}: '{value}'")
            time.sleep(0.5)  # Small delay between writes to give watch time to process
        except Exception as e:
            print(f"Client [watch]: failed to write update {i}: {e}")

    writer.close()  # Done writing

    # If no writes succeeded at all, we can't verify anything
    if not written_values:
        print("Client [watch]: no writes succeeded, skipping validation")
        watcher.close()
        return

    # STEP 5: Wait for the watch thread to collect all events (or timeout)
    watch_thread.join(timeout=WATCH_TIMEOUT)  # Wait up to 15 seconds for the thread to finish

    watcher.close()  # Close the watcher connection

    print(f"Client [watch]: received {len(received_values)} events for {len(written_values)} writes")

    # STEP 6: VALIDATE — Check for impossible duplicate events
    # Getting MORE events than writes would mean etcd is generating phantom/duplicate events
    if len(received_values) > len(written_values):
        unreachable(
            "Watch received more events than writes",
            {"writes": len(written_values), "events": len(received_values)},
        )

    # STEP 7: VALIDATE — Check that received values match what was written
    # Compare each received event value against the corresponding written value
    values_match = True
    for i in range(min(len(received_values), len(written_values))):
        if received_values[i] != written_values[i]:
            values_match = False
            print(f"Client [watch]: mismatch at index {i}: expected '{written_values[i]}', got '{received_values[i]}'")
            break

    # If we received events, their values must be correct
    always_or_unreachable(
        values_match,
        "Watch event values match written values",
        {"written": written_values, "received": received_values},
    )

    # STEP 8: VALIDATE — Check that events arrived in the correct order
    # etcd guarantees ordered delivery — events should match write order
    events_in_order = True
    for i in range(1, len(received_values)):
        # For each pair of consecutive received events, check their positions in written_values
        if received_values[i] in written_values and received_values[i - 1] in written_values:
            if written_values.index(received_values[i]) <= written_values.index(received_values[i - 1]):
                events_in_order = False  # Later event appeared before earlier one
                break

    # If we received events, they must be in order
    always_or_unreachable(
        events_in_order,
        "Watch events arrive in correct order",
        {"received_order": received_values},
    )

    # STEP 9: VALIDATE — Check that ALL events were received (no event loss)
    all_events_received = len(received_values) == len(written_values)
    # Must happen at least once — some runs may lose events due to faults, and that's OK
    sometimes(
        all_events_received,
        "All watch events received",
        {"expected": len(written_values), "received": len(received_values)},
    )

    print(f"Client [watch]: values_match={values_match}, in_order={events_in_order}, all_received={all_events_received}")

    # STEP 10: Mark that the test ran to completion
    reachable("Watch consistency test completed end-to-end", {})
    print("Client [watch]: watch consistency test complete!")
    time.sleep(1)  # Brief pause to let the SDK flush output to the file


# Standard Python entry point
if __name__ == "__main__":
    test_watch_consistency()
