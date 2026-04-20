# API Guide

Base URL: `http://localhost:8000`

Authentication header for all protected routes:

```http
Authorization: Bearer <API_KEY>
```

Load API key from `.env`:

```bash
API_KEY=$(grep '^API_KEY=' .env | cut -d= -f2)
```

## Health & readiness

```bash
curl -s http://localhost:8000/api/v1/healthz
curl -s http://localhost:8000/api/v1/readyz
curl -s http://localhost:8000/api/v1/metrics | head -n 20
```

## Single upload

```bash
curl -s -X POST http://localhost:8000/api/v1/uploads \
  -H "Authorization: Bearer $API_KEY" \
  -F "file=@tests/fixtures/valid.jpg"
```

Response:

```json
{
  "job_id": "job_...",
  "status": "queued",
  "status_url": "/api/v1/jobs/job_...",
  "created_at": "..."
}
```

## Batch upload (up to 5)

```bash
curl -s -X POST http://localhost:8000/api/v1/uploads \
  -H "Authorization: Bearer $API_KEY" \
  -F "files[]=@tests/fixtures/valid.jpg" \
  -F "files[]=@tests/fixtures/valid.jpg" \
  -F "files[]=@tests/fixtures/valid.jpg" \
  -F "files[]=@tests/fixtures/valid.jpg" \
  -F "files[]=@tests/fixtures/valid.jpg"
```

## Idempotency key

Same key + same file returns same `job_id`:

```bash
curl -s -X POST http://localhost:8000/api/v1/uploads \
  -H "Authorization: Bearer $API_KEY" \
  -H "Idempotency-Key: idem-1" \
  -F "file=@tests/fixtures/valid.jpg"
```

Same key + different file returns conflict:

```bash
curl -s -X POST http://localhost:8000/api/v1/uploads \
  -H "Authorization: Bearer $API_KEY" \
  -H "Idempotency-Key: idem-1" \
  -F "file=@/tmp/different.jpg"
```

## Job status polling

```bash
JOB_ID=<job_id>
while true; do
  OUT=$(curl -s "http://localhost:8000/api/v1/jobs/$JOB_ID" \
    -H "Authorization: Bearer $API_KEY")
  echo "$OUT"
  STATUS=$(echo "$OUT" | python3 -c 'import sys,json;print(json.load(sys.stdin)["status"])')
  [ "$STATUS" = "done" ] && break
  [ "$STATUS" = "failed" ] && break
  sleep 1
done
```

## Retry failed job

```bash
curl -s -X POST "http://localhost:8000/api/v1/jobs/$JOB_ID/retry" \
  -H "Authorization: Bearer $API_KEY"
```

## Report retrieval formats

```bash
REPORT_ID=<report_id>

# JSON
curl -s "http://localhost:8000/api/v1/reports/$REPORT_ID" \
  -H "Authorization: Bearer $API_KEY" \
  -H "Accept: application/json"

# Markdown
curl -s "http://localhost:8000/api/v1/reports/$REPORT_ID" \
  -H "Authorization: Bearer $API_KEY" \
  -H "Accept: text/markdown"

# HTML
curl -s "http://localhost:8000/api/v1/reports/$REPORT_ID" \
  -H "Authorization: Bearer $API_KEY" \
  -H "Accept: text/html" > report.html

# PDF
curl -s "http://localhost:8000/api/v1/reports/$REPORT_ID" \
  -H "Authorization: Bearer $API_KEY" \
  -H "Accept: application/pdf" > report.pdf
```

## Webhook upload

Container-to-container endpoint:

```bash
curl -s -X POST http://localhost:8000/api/v1/uploads \
  -H "Authorization: Bearer $API_KEY" \
  -F "file=@tests/fixtures/valid.jpg" \
  -F "webhook_url=http://webhook-echo:8080/hook"
```

Host-routable endpoint:

```bash
curl -s -X POST http://localhost:8000/api/v1/uploads \
  -H "Authorization: Bearer $API_KEY" \
  -F "file=@tests/fixtures/valid.jpg" \
  -F "webhook_url=http://host.docker.internal:8888/hook"
```

View webhook logs:

```bash
docker compose logs --tail=100 webhook-echo
```

## GDPR-style delete

```bash
curl -s -X DELETE "http://localhost:8000/api/v1/jobs/$JOB_ID" \
  -H "Authorization: Bearer $API_KEY"
```

## Frontend

- End-user mode: `http://localhost:5173/`
- Dev/operator mode: `http://localhost:5173/?mode=dev`
