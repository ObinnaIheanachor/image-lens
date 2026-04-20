# Image Insight

Current build includes Day 1-4 backend features with a working runtime path:
- Authenticated upload endpoint (`Bearer API_KEY`)
- Async job processing (`inmemory` queue now, `rq` seam implemented)
- Retry endpoint for failed jobs
- Local webhook callback dispatch
- Readiness checks with dependency breakdown
- Object store seam (`local` now, `minio` seam implemented)

## Prereqs
- Python 3.11+
- Docker Desktop (primary intended runtime)
- WeasyPrint native deps (for upcoming PDF work):
  - `brew install pango cairo gdk-pixbuf libffi`

## Quickstart (lite)
```bash
cp .env.example .env
# regenerate API key
openssl rand -hex 32
# set API_KEY in .env

make demo-lite
```

## API auth
All core endpoints require:
```http
Authorization: Bearer <API_KEY>
```

## Core flow (curl)
```bash
API_KEY=$(grep '^API_KEY=' .env | cut -d= -f2)

curl -s -X POST http://localhost:8000/api/v1/uploads \
  -H "Authorization: Bearer $API_KEY" \
  -F "file=@tests/fixtures/valid.jpg"

curl -s http://localhost:8000/api/v1/jobs/<job_id> \
  -H "Authorization: Bearer $API_KEY"

curl -s http://localhost:8000/api/v1/reports/<report_id> \
  -H "Authorization: Bearer $API_KEY"
```

## Retry flow test
```bash
curl -s -X POST http://localhost:8000/api/v1/uploads \
  -H "Authorization: Bearer $API_KEY" \
  -F "file=@tests/fixtures/valid.jpg" \
  -F 'metadata={"force_fail_once":true}'

curl -s -X POST http://localhost:8000/api/v1/jobs/<job_id>/retry \
  -H "Authorization: Bearer $API_KEY"
```

## Webhook test (offline)
Use local echo service in compose:
- `http://webhook-echo:8080` from containers
- `http://localhost:${WEBHOOK_ECHO_PORT:-8888}` from host

Upload with:
```bash
-F "webhook_url=http://localhost:8888/hook"
```

## Readiness
- `GET /api/v1/healthz` -> liveness
- `GET /api/v1/readyz` -> dependency status; returns `503` when degraded

## Provider switch (documented)
Default in `.env.example`:
- `AI_PROVIDER=mock`

Planned Claude path:
- `AI_PROVIDER=claude`
- `ANTHROPIC_API_KEY=<your_key>`

See [trade-offs doc](docs/trade-offs.md) for rationale.
