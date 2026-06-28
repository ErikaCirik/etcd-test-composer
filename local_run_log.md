# Local Run Log — etcd Test Drivers

## 1. Build the Client Docker Image

Since the full `Dockerfile.client` has a Rust cargo build step that fails due to SSL certificate issues in the container, I created a simplified `Dockerfile.client.local` that only includes the Python components needed for my tests.

```bash
cd /Users/erikacirikaite/Documents/GitHub/etcd-test-composer/test-template

docker build -t etcd-client:latest -f Dockerfile.client.local .
```

**What it does:** Builds a Docker image tagged `etcd-client:latest` from the local-only Dockerfile. This image contains Python, the etcd3 client library, the Antithesis SDK, the entrypoint script, and both test drivers.

**Output:** Image built successfully.

---

## 2. Start the etcd Cluster

```bash
cd /Users/erikacirikaite/Documents/GitHub/etcd-test-composer/config

docker compose up -d
```

**What it does:** Starts 4 containers in the background:
- `etcd0`, `etcd1`, `etcd2` — a 3-node etcd cluster
- `client` — runs `/entrypoint.py`, which checks cluster health and sends `setup_complete`

**Output:** All 4 containers started successfully.

---

## 3. Verify the Cluster is Healthy

```bash
docker logs client
```

**What it does:** Shows the client container's entrypoint output to confirm the cluster is ready.

**Output:**
```
Client [entrypoint]: starting...
Client [entrypoint]: checking cluster health...
Client [entrypoint]: connection successful with etcd0
Client [entrypoint]: connection successful with etcd1
Client [entrypoint]: connection successful with etcd2
Client [entrypoint]: cluster is healthy!
```

---

## 4. Run the Lease TTL Driver (Eventually)

```bash
docker compose exec client bash -c \
  'ANTITHESIS_SDK_LOCAL_OUTPUT=/tmp/sdk_lease.json python3 -u /opt/antithesis/python-lease-ttl/eventually_driver_lease_ttl.py'
```

**What it does:** Executes the lease TTL validation driver inside the running client container. The `ANTITHESIS_SDK_LOCAL_OUTPUT` environment variable tells the Antithesis SDK to write assertion results to `/tmp/sdk_lease.json` in structured JSON format.

**Output:**
```
Client [lease-ttl]: starting lease TTL validation...
Client: connected to etcd2
Client [lease-ttl]: created lease with ID 7043241738945431566 and TTL 10s
Client [lease-ttl]: attached key 'lease-test-CNuPi2zs' to lease 7043241738945431566
Client: connected to etcd0
Client [lease-ttl]: verified key 'lease-test-CNuPi2zs' on different node, value matches: True
Client [lease-ttl]: lease ID matches across nodes: True
Client [lease-ttl]: waiting 15s for lease to expire...
Client: connected to etcd1
Client [lease-ttl]: key expired correctly: True
Client [lease-ttl]: lease TTL validation complete!
```

**ANTITHESIS_SDK_LOCAL_OUTPUT (Lease TTL):**
```json
{"antithesis_sdk": {"language": {"name": "Python", "version": "3.14.4 (main, Apr  8 2026, 04:02:31) [GCC 15.2.0]"}, "sdk_version": "0.2.0", "protocol_version": "1.0.0"}}
{"antithesis_assert": {"condition": true, "must_hit": true, "hit": true, "id": "Lease creation succeeds", "message": "Lease creation succeeds", "display_type": "Sometimes", "assert_type": "sometimes", "location": {"file": "/opt/antithesis/python-lease-ttl/eventually_driver_lease_ttl.py", "function": "test_lease_ttl", "class": "", "begin_line": 32, "begin_column": 0}, "details": {"lease_id": 7043241738945431566}}}
{"antithesis_assert": {"condition": true, "must_hit": false, "hit": true, "id": "Leased key value is consistent across nodes", "message": "Leased key value is consistent across nodes", "display_type": "AlwaysOrUnreachable", "assert_type": "always", "location": {"file": "/opt/antithesis/python-lease-ttl/eventually_driver_lease_ttl.py", "function": "test_lease_ttl", "class": "", "begin_line": 52, "begin_column": 0}, "details": {"expected": "val-YTKM1ug5", "got": "val-YTKM1ug5"}}}
{"antithesis_assert": {"condition": true, "must_hit": false, "hit": true, "id": "Lease ID is consistent across nodes", "message": "Lease ID is consistent across nodes", "display_type": "AlwaysOrUnreachable", "assert_type": "always", "location": {"file": "/opt/antithesis/python-lease-ttl/eventually_driver_lease_ttl.py", "function": "test_lease_ttl", "class": "", "begin_line": 61, "begin_column": 0}, "details": {"expected": 7043241738945431566, "got": 7043241738945431566}}}
{"antithesis_assert": {"condition": true, "must_hit": false, "hit": true, "id": "Key is removed after lease expiry", "message": "Key is removed after lease expiry", "display_type": "AlwaysOrUnreachable", "assert_type": "always", "location": {"file": "/opt/antithesis/python-lease-ttl/eventually_driver_lease_ttl.py", "function": "test_lease_ttl", "class": "", "begin_line": 82, "begin_column": 0}, "details": {"key": "lease-test-CNuPi2zs", "value_found": null}}}
{"antithesis_assert": {"condition": true, "must_hit": true, "hit": true, "id": "Lease expiry cleans up keys", "message": "Lease expiry cleans up keys", "display_type": "Sometimes", "assert_type": "sometimes", "location": {"file": "/opt/antithesis/python-lease-ttl/eventually_driver_lease_ttl.py", "function": "test_lease_ttl", "class": "", "begin_line": 87, "begin_column": 0}, "details": {"key": "lease-test-CNuPi2zs"}}}
```

---

## 5. Run the Watch Consistency Driver (Anytime)

```bash
docker compose exec client bash -c \
  'ANTITHESIS_SDK_LOCAL_OUTPUT=/tmp/sdk_watch.json python3 -u /opt/antithesis/python-watch-consistency/anytime_driver_watch_consistency.py'
```

**What it does:** Executes the watch consistency driver. It writes to a key from one etcd node while watching it from another, then verifies all events arrived correctly.

**Output:**
```
Client [watch]: starting watch consistency test...
Client [watch]: created key 'watch-test-uBf0aXX4' on etcd0
Client [watch]: watch established on 'watch-test-uBf0aXX4' via etcd2
Client [watch]: wrote update 0: 'update-0-EpQRna8A'
Client [watch]: wrote update 1: 'update-1-GDYrSnn2'
Client [watch]: wrote update 2: 'update-2-1uipr44c'
Client [watch]: wrote update 3: 'update-3-xcHSnrMc'
Client [watch]: wrote update 4: 'update-4-8cko270i'
Client [watch]: received 5 events for 5 writes
Client [watch]: values_match=True, in_order=True, all_received=True
Client [watch]: watch consistency test complete!
```

**ANTITHESIS_SDK_LOCAL_OUTPUT (Watch Consistency):**
```json
{"antithesis_sdk": {"language": {"name": "Python", "version": "3.14.4 (main, Apr  8 2026, 04:02:31) [GCC 15.2.0]"}, "sdk_version": "0.2.0", "protocol_version": "1.0.0"}}
{"antithesis_assert": {"condition": true, "must_hit": true, "hit": true, "id": "Watch established successfully", "message": "Watch established successfully", "display_type": "Sometimes", "assert_type": "sometimes", "location": {"file": "/opt/antithesis/python-watch-consistency/anytime_driver_watch_consistency.py", "function": "test_watch_consistency", "class": "", "begin_line": 69, "begin_column": 0}, "details": {"key": "watch-test-uBf0aXX4", "writer": "etcd0", "watcher": "etcd2"}}}
{"antithesis_assert": {"condition": true, "must_hit": false, "hit": true, "id": "Watch event values match written values", "message": "Watch event values match written values", "display_type": "AlwaysOrUnreachable", "assert_type": "always", "location": {"file": "/opt/antithesis/python-watch-consistency/anytime_driver_watch_consistency.py", "function": "test_watch_consistency", "class": "", "begin_line": 109, "begin_column": 0}, "details": {"written": ["update-0-EpQRna8A", "update-1-GDYrSnn2", "update-2-1uipr44c", "update-3-xcHSnrMc", "update-4-8cko270i"], "received": ["update-0-EpQRna8A", "update-1-GDYrSnn2", "update-2-1uipr44c", "update-3-xcHSnrMc", "update-4-8cko270i"]}}}
{"antithesis_assert": {"condition": true, "must_hit": false, "hit": true, "id": "Watch events arrive in correct order", "message": "Watch events arrive in correct order", "display_type": "AlwaysOrUnreachable", "assert_type": "always", "location": {"file": "/opt/antithesis/python-watch-consistency/anytime_driver_watch_consistency.py", "function": "test_watch_consistency", "class": "", "begin_line": 122, "begin_column": 0}, "details": {"received_order": ["update-0-EpQRna8A", "update-1-GDYrSnn2", "update-2-1uipr44c", "update-3-xcHSnrMc", "update-4-8cko270i"]}}}
{"antithesis_assert": {"condition": true, "must_hit": true, "hit": true, "id": "All watch events received", "message": "All watch events received", "display_type": "Sometimes", "assert_type": "sometimes", "location": {"file": "/opt/antithesis/python-watch-consistency/anytime_driver_watch_consistency.py", "function": "test_watch_consistency", "class": "", "begin_line": 129, "begin_column": 0}, "details": {"expected": 5, "received": 5}}}
{"antithesis_assert": {"condition": true, "must_hit": true, "hit": true, "id": "Watch consistency test completed end-to-end", "message": "Watch consistency test completed end-to-end", "display_type": "Reachable", "assert_type": "reachability", "location": {"file": "/opt/antithesis/python-watch-consistency/anytime_driver_watch_consistency.py", "function": "test_watch_consistency", "class": "", "begin_line": 137, "begin_column": 0}, "details": {}}}
```

---

## 6. Clean Up

```bash
cd /Users/erikacirikaite/Documents/GitHub/etcd-test-composer/config

docker compose down
```

**What it does:** Stops and removes all containers and the network created by docker compose.

---

## Notes

- The `Dockerfile.client.local` was created only for local testing because the original `Dockerfile.client` has a Rust cargo build step that fails locally due to SSL certificate issues inside the Docker build context. The original `Dockerfile.client` (with all languages) is the one that should be committed and used in Antithesis.
- The `ANTITHESIS_SDK_LOCAL_OUTPUT` environment variable must point to a **file path** (not a directory) for the SDK to write assertion output.
- The Antithesis SDK's random module falls back to Python's `random.getrandbits(64)` when running outside the Antithesis platform, so `helper.py` functions work locally without modification.
- The watch driver produces a harmless "Channel closed" error from the etcd3 library's internal watcher thread when the client connection is closed after the test completes. This does not affect test results.

---

## Troubleshooting

| Problem | Fix |
|---|---|
| "No such container: client" | Run `docker compose up -d` again |
| "cluster is not healthy" | Wait longer: `sleep 20` then check `docker logs client` again |
| "No such file" for the driver | Rebuild: go back to step 1 and `docker build` again |
| Watch test shows 0 events | This can happen occasionally — run it again |
| Any other error | `docker compose down` then start from step 1 |
