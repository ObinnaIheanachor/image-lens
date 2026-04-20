# Runbook

## Start/stop

```bash
# full stack
docker compose up --build

# full stack detached
docker compose up -d --build

# stop
docker compose down
```

Lite profile:

```bash
docker compose -f docker-compose.lite.yml up --build
```

## Verify service health

```bash
curl -s http://localhost:8000/api/v1/healthz
curl -s http://localhost:8000/api/v1/readyz
```

Expected `readyz` healthy shape:

```json
{"status":"ok","dependencies":{"database":"ok","queue":"ok","object_store":"ok"}}
```

## Common issues

### Port already allocated

Symptoms: compose fails with `Bind for 0.0.0.0:<port> failed`.

Fix:

```bash
# Example: find container using a port
docker ps --format "table {{.ID}}\t{{.Names}}\t{{.Ports}}" | grep 9000

# or move project ports in .env, then restart
docker compose down
docker compose up --build
```

### Worker crash on startup

Check:

```bash
docker compose logs --tail=200 worker
```

Typical fix path: rebuild after code/dependency updates.

```bash
docker compose up --build api worker
```

### PDF endpoint returns 503

Check API logs:

```bash
docker compose logs --tail=200 api
```

Cause: missing native libs in image. Ensure latest Dockerfile image is rebuilt.

```bash
docker compose up --build api worker
```

### `readyz` returns 503 degraded

Inspect dependency statuses from response payload and logs:

```bash
curl -s -i http://localhost:8000/api/v1/readyz
docker compose logs --tail=200 api redis postgres minio
```

Recovery: restart failing dependency and worker/API if needed.

```bash
docker compose restart redis postgres minio api worker
```

## Debug commands

```bash
# API
docker compose logs -f api

# worker
docker compose logs -f worker

# webhook capture
docker compose logs -f webhook-echo
```

## Smoke-test script

```bash
API_KEY=$(grep '^API_KEY=' .env | cut -d= -f2)

UP=$(curl -s -X POST http://localhost:8000/api/v1/uploads \
  -H "Authorization: Bearer $API_KEY" \
  -F "file=@tests/fixtures/valid.jpg")

echo "$UP"
JOB_ID=$(echo "$UP" | python3 -c 'import sys,json;print(json.load(sys.stdin)["job_id"])')

while true; do
  J=$(curl -s http://localhost:8000/api/v1/jobs/$JOB_ID -H "Authorization: Bearer $API_KEY")
  echo "$J"
  S=$(echo "$J" | python3 -c 'import sys,json;print(json.load(sys.stdin)["status"])')
  [ "$S" = "done" ] && break
  [ "$S" = "failed" ] && break
  sleep 1
done
```
