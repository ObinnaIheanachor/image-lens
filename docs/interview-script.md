# 5-Minute Interview Script (Scenarios A–G)

## Setup (0:00-0:20)

```bash
API_KEY=$(grep '^API_KEY=' .env | cut -d= -f2)
```

Open:
- Frontend: `http://localhost:5173/`
- Optional dev controls: `http://localhost:5173/?mode=dev`

## Scenario A: Valid upload happy path (0:20-1:10)

Action:
- Upload `tests/fixtures/valid.jpg` from frontend.
- Show status transitions to done.
- Open report page and download PDF.

Talking point:
- Async processing keeps upload path fast while worker does analysis.

## Scenario B: Invalid upload (1:10-1:40)

Action:

```bash
curl -s -X POST http://localhost:8000/api/v1/uploads \
  -H "Authorization: Bearer $API_KEY" \
  -F "file=@tests/fixtures/corrupt.jpg"
```

Expected: `422 image_decode_failed`.

Talking point:
- Validation failures are explicit and surfaced as typed errors.

## Scenario C: Duplicate upload with idempotency (1:40-2:05)

Action:

```bash
curl -s -X POST http://localhost:8000/api/v1/uploads \
  -H "Authorization: Bearer $API_KEY" \
  -H "Idempotency-Key: demo-dup" \
  -F "file=@tests/fixtures/valid.jpg"

curl -s -X POST http://localhost:8000/api/v1/uploads \
  -H "Authorization: Bearer $API_KEY" \
  -H "Idempotency-Key: demo-dup" \
  -F "file=@tests/fixtures/valid.jpg"
```

Expected: same `job_id` both times.

Talking point:
- Safe retries without duplicate work.

## Scenario D: Provider failure + retry path (2:05-2:45)

Action:

```bash
UP=$(curl -s -X POST http://localhost:8000/api/v1/uploads \
  -H "Authorization: Bearer $API_KEY" \
  -F "file=@tests/fixtures/valid.jpg" \
  -F 'metadata={"force_fail_once":true}')
JOB_ID=$(echo "$UP" | python3 -c 'import sys,json;print(json.load(sys.stdin)["job_id"])')

curl -s http://localhost:8000/api/v1/jobs/$JOB_ID -H "Authorization: Bearer $API_KEY"
curl -s -X POST http://localhost:8000/api/v1/jobs/$JOB_ID/retry -H "Authorization: Bearer $API_KEY"
```

Talking point:
- Failure state is explicit and recoverable by API contract.

## Scenario E: Batch upload burst (2:45-3:15)

Action:

```bash
curl -s -X POST http://localhost:8000/api/v1/uploads \
  -H "Authorization: Bearer $API_KEY" \
  -F "files[]=@tests/fixtures/valid.jpg" \
  -F "files[]=@tests/fixtures/valid.jpg" \
  -F "files[]=@tests/fixtures/valid.jpg" \
  -F "files[]=@tests/fixtures/valid.jpg" \
  -F "files[]=@tests/fixtures/valid.jpg"
```

Talking point:
- Queue decouples ingress from processing and absorbs bursts.

## Scenario F: Webhook callback (3:15-3:45)

Action:

```bash
curl -s -X POST http://localhost:8000/api/v1/uploads \
  -H "Authorization: Bearer $API_KEY" \
  -F "file=@tests/fixtures/valid.jpg" \
  -F "webhook_url=http://host.docker.internal:8888/hook"

docker compose logs --tail=60 webhook-echo
```

Talking point:
- Poll and push delivery models are both supported.

## Scenario G: GDPR deletion + readiness degradation (3:45-4:40)

Action (delete):

```bash
curl -s -X DELETE http://localhost:8000/api/v1/jobs/<job_id> \
  -H "Authorization: Bearer $API_KEY"
```

Action (degrade probe):

```bash
docker compose stop redis
curl -s -i http://localhost:8000/api/v1/readyz
docker compose start redis
```

Talking point:
- Operational introspection is first-class (`readyz`, `metrics`).

## Close (4:40-5:00)

Highlight seams:
- `src/queue/*` for queue backend swap
- `src/storage/*` for object store swap
- `src/reports/*` for format/rendering surface
- `src/analyzers/*` for provider swap (mock default, Claude path)

Final line:
- "The demo runs locally with production-shaped interfaces and explicit failure-handling paths."
