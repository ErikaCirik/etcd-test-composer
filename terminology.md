# Terminology Guide

All technical terms used in this project, explained simply.

| Term | What it means | Example |
|---|---|---|
| **etcd** | A distributed database that stores small pieces of data (key-value pairs) across multiple computers. Used by systems like Kubernetes to coordinate. | Storing `leader = server-3` so all servers know who's in charge. |
| **Node** | One computer (or container) running etcd in the cluster. There are 3: etcd0, etcd1, etcd2. | etcd0 is one node in the 3-node cluster. |
| **Cluster** | A group of nodes working together as one system. If one dies, the others keep going. | The 3 etcd nodes form a cluster. |
| **Key-value pair** | A piece of data stored as a name (key) and its content (value), like a dictionary entry. | Key: `username`, Value: `alice`. |
| **Put** | Writing a key-value pair into etcd. | `client.put("color", "blue")` stores the value "blue" under the key "color". |
| **Get** | Reading a value from etcd by its key. | `client.get("color")` returns "blue". |
| **Lease** | A temporary permission attached to a key. When the lease expires, the key is automatically deleted. | A 10-second lease on key `lock-owner` — after 10 seconds, the key disappears. |
| **TTL (Time To Live)** | How many seconds a lease lasts before it expires. | A lease with TTL=10 expires 10 seconds after creation. |
| **Watch** | Subscribing to changes on a key. When someone updates the key, you get notified. | Watching key `config` — whenever it changes, your app gets an event. |
| **Watch event** | A notification you receive when a watched key changes. Contains the new value. | Key `config` changed from "v1" to "v2" → you receive an event with value "v2". |
| **Docker** | A tool that packages software into isolated containers so it runs the same way everywhere. | Packaging the test code + Python + libraries into one container. |
| **Container** | A lightweight, isolated environment running a single application. Like a mini virtual computer. | The `client` container runs the test code. The `etcd0` container runs one etcd node. |
| **Docker image** | A blueprint for creating containers. Built from a Dockerfile. | `etcd-client:latest` is the image; when you run it, it becomes a container. |
| **Dockerfile** | A recipe file listing the steps to build a Docker image (install dependencies, copy files, etc.). | `Dockerfile.client` says: install Python, copy test scripts, install Antithesis SDK. |
| **docker-compose.yml** | A configuration file that defines and starts multiple containers together as a group. | The file starts 3 etcd nodes + 1 client container and connects them on the same network. |
| **docker compose up** | The command to start all containers defined in docker-compose.yml. | `docker compose up -d` starts everything in the background. |
| **docker compose exec** | The command to run something inside an already-running container. | `docker compose exec client python3 script.py` runs a Python script inside the client container. |
| **docker compose down** | The command to stop and remove all containers started by docker compose. | Cleans up everything after testing. |
| **Antithesis** | A testing platform that finds bugs by running your software while injecting random faults (crashes, network issues). | Running the etcd cluster inside Antithesis, which randomly kills nodes to see if data gets corrupted. |
| **Fault injection** | Intentionally breaking things (crashing nodes, cutting network connections) to test if the system handles it correctly. | Antithesis disconnects etcd1 from the network to see if etcd0 and etcd2 still work. |
| **Network partition** | When some nodes can't communicate with others, splitting the cluster into isolated groups. | etcd0 can talk to etcd1, but neither can reach etcd2 — the cluster is "split." |
| **Test Composer** | Antithesis's system for organizing and running test scripts. It looks for scripts in `/opt/antithesis/test/v1/main/`. | Placing `eventually_lease_ttl.sh` in that directory tells the Test Composer to run it. |
| **Driver command** | A test script that the Test Composer runs. It does something to the system and checks results. | `eventually_driver_lease_ttl.py` is a driver that tests lease behavior. |
| **Eventually driver** | A driver that must succeed at least once during the test. Failures are OK as long as it passes at least once. | The lease test — it's fine if faults make it fail a few times, as long as it works once. |
| **Anytime driver** | A driver that runs repeatedly throughout the test, giving it many chances to catch intermittent bugs. | The watch test — it runs over and over, catching bugs that only happen sometimes. |
| **setup_complete** | A signal sent to Antithesis saying "the system is ready, you can start testing and injecting faults now." | The entrypoint sends this after all 3 etcd nodes are healthy. |
| **Assertion** | A statement that declares something must be true. If it's false, a bug is reported. | "The value I read must match the value I wrote." |
| **SDK (Software Development Kit)** | A library of code provided by Antithesis that you use in your tests to make assertions and use randomness. | `from antithesis.assertions import always` — importing the assertion function from the SDK. |
| **`sometimes`** | An assertion type: the condition must be true at least once across all runs. | `sometimes(success, "Puts succeed")` — at least one put request must work. |
| **`always_or_unreachable`** | An assertion type: every time this line runs, the condition must be true. But it's OK if the line is never reached. | `always_or_unreachable(value_matches, "Values consistent")` — if I read a value, it must be correct. |
| **`unreachable`** | An assertion type: this line of code should never execute. If it does, it's a bug. | `unreachable("Data corrupted")` — placed in a code path that handles impossible corruption. |
| **`reachable`** | An assertion type: this line of code must execute at least once. Proves the test ran to completion. | `reachable("Test completed")` — placed at the end of the test. |
| **ANTITHESIS_SDK_LOCAL_OUTPUT** | An environment variable that tells the SDK to write assertion results to a file when running outside Antithesis. | Setting it to `/tmp/sdk_output.json` makes the SDK log all assertion results there. |
| **JSON (JavaScript Object Notation)** | A text format for structured data, using key-value pairs and lists. Easy for both humans and computers to read. | `{"name": "alice", "age": 30}` is a JSON object. |
| **JSONL** | JSON Lines — a file where each line is a separate JSON object. The SDK output uses this format. | Line 1: `{"assert": "Lease created"}`, Line 2: `{"assert": "Value matches"}`. |
| **gRPC** | A communication protocol etcd uses internally for nodes to talk to each other and for clients to connect. | The Python client uses gRPC under the hood when it calls `etcd3.client()`. |
| **Consensus** | The process by which all nodes in a cluster agree on the same data. etcd uses the Raft algorithm for this. | When you write to etcd0, consensus ensures etcd1 and etcd2 also get the update. |
| **Replication** | Copying data from one node to all other nodes so everyone has the same information. | Writing `color=blue` to etcd0 — replication copies it to etcd1 and etcd2. |
| **Leader election** | The process of choosing one node to be the "leader" that coordinates writes. If the leader dies, a new one is chosen. | etcd0 is the leader. It crashes. etcd1 and etcd2 vote, and etcd1 becomes the new leader. |
| **Split-brain** | A dangerous situation where two parts of a cluster each think they're in charge, leading to conflicting data. | After a network partition, etcd0 thinks it's the leader AND etcd2 thinks it's the leader. |
| **Distributed lock** | A mechanism to ensure only one process can do something at a time, across multiple machines. Uses leases. | Server A holds a lock on "database-migration" — Server B must wait until A's lease expires. |
| **Service discovery** | A way for services to find each other by registering themselves in etcd with a lease. If they die, the lease expires and they're removed. | Web server registers `services/web-1 = 192.168.1.5` with a 30s lease. If it crashes, the entry disappears. |
| **Shell script (.sh)** | A text file containing commands to run in a terminal. Antithesis Test Composer requires these as entry points. | `eventually_lease_ttl.sh` just runs `python3 our_test.py`. |
| **Entrypoint** | The first script that runs when a container starts. In this project, it checks cluster health and signals setup_complete. | `entrypoint.py` runs when the client container starts, waits for all nodes to be healthy. |
| **Environment variable** | A setting passed to a program from outside, like a configuration switch. | `ANTITHESIS_SDK_LOCAL_OUTPUT=/tmp/output.json` tells the SDK where to write. |
| **Daemon thread** | A background thread that automatically stops when the main program exits. Won't keep the program running. | The watch listener runs in a daemon thread — when the test finishes, the thread stops too. |
