# Quick Run Cheat Sheet

Copy-paste these commands in order. The whole flow takes about 2 minutes.

## Start Everything

```bash
# 1. Go to the test-template folder and build the Docker image
cd ~/Documents/GitHub/etcd-test-composer/test-template
docker build -t etcd-client:latest -f Dockerfile.client.local .

# 2. Go to the config folder and start the cluster
cd ~/Documents/GitHub/etcd-test-composer/config
docker compose up -d

# 3. Wait 10 seconds for the cluster to start, then check it's healthy
sleep 10
docker logs client
```

You should see:
```
Client [entrypoint]: cluster is healthy!
```

## Run the Lease Test

```bash
docker compose exec client bash -c \
  'ANTITHESIS_SDK_LOCAL_OUTPUT=/tmp/sdk_lease.json python3 -u /opt/antithesis/python-lease-ttl/eventually_driver_lease_ttl.py'
```

Takes ~25 seconds (15s waiting for lease to expire). You should see:
```
Client [lease-ttl]: key expired correctly: True
Client [lease-ttl]: lease TTL validation complete!
```

### See the SDK assertion output:

```bash
docker compose exec client bash -c 'cat /tmp/sdk_lease.json'
```

## Run the Watch Test

```bash
docker compose exec client bash -c \
  'ANTITHESIS_SDK_LOCAL_OUTPUT=/tmp/sdk_watch.json python3 -u /opt/antithesis/python-watch-consistency/anytime_driver_watch_consistency.py'
```

Takes ~15 seconds. You should see:
```
Client [watch]: received 5 events for 5 writes
Client [watch]: values_match=True, in_order=True, all_received=True
Client [watch]: watch consistency test complete!
```

### See the SDK assertion output:

```bash
docker compose exec client bash -c 'cat /tmp/sdk_watch.json'
```

## Clean Up

```bash
docker compose down
```

## If Something Goes Wrong

| Problem | Fix |
|---|---|
| "No such container: client" | Run `docker compose up -d` again |
| "cluster is not healthy" | Wait longer: `sleep 20` then check `docker logs client` again |
| "No such file" for the driver | Rebuild: go back to step 1 and `docker build` again |
| Watch test shows 0 events | This can happen occasionally — run it again |
| Any other error | `docker compose down` then start from step 1 |
