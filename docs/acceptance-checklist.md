# Acceptance Checklist Audit

Date: 2026-04-20

Legend:
- PASS: validated in current code/runtime
- PARTIAL: implemented but not fully proven for target criterion wording
- FAIL: known gap
- PENDING: not yet validated in current environment

## Criteria status

1. `docker compose up --build` full-stack + frontend end-to-end: PASS  
Proof: `docker compose up --build`, then `curl -s http://localhost:8000/api/v1/readyz`, open `http://localhost:5173/`.
2. Lite profile offline fallback: PENDING  
Proof command: `docker compose -f docker-compose.lite.yml up --build`.
3. Valid upload returns `job_id` within 500ms: PASS  
Proof: `curl -w '%{time_total}' ... /uploads`.
4. Mock job reaches `done` and report available: PASS  
Proof: `GET /jobs/{id}` polling then `GET /reports/{id}`.
5. Report formats JSON/MD/HTML/PDF: PASS  
Proof: `Accept: application/json|text/markdown|text/html|application/pdf`.
6. Idempotency same key => same job: PASS  
Proof: repeated upload with `Idempotency-Key` + same image.
7. Fake `.jpg` with PDF payload => `unsupported_media_type`: PASS  
Proof: upload `%PDF-` payload as `.jpg` returns `400 unsupported_media_type`.
8. 25MB file => `413 payload_too_large`: PENDING  
Proof command: upload synthetic 25MB file.
9. Zero-byte file => `400 empty_file`: PASS  
Proof: upload `/dev/null` as file.
10. Batch upload of 5 => 5 jobs/reports: PASS  
Proof: `files[]` x5 upload + polling.
11. Claude invalid key failure path: PENDING  
Proof command: run with `AI_PROVIDER=claude` + invalid `ANTHROPIC_API_KEY`.
12. Mock default/offline demo: PASS  
Proof: `.env` default `AI_PROVIDER=mock`.
13. Retry failed job re-queues: PASS  
Proof: forced fail metadata + `POST /jobs/{id}/retry`.
14. GDPR delete semantics (bytes removed + audit retained): PARTIAL  
Current: `DELETE /jobs/{id}` marks deleted.
15. Webhook delivered within 30s: PASS  
Proof: `webhook-echo` logs show POST payload.
16. `/readyz` dependency degradation: PASS  
Proof: `docker compose stop redis` then `GET /readyz` => 503.
17. `/metrics` exposes Prometheus metrics: PASS  
Proof: `GET /api/v1/metrics` includes counters/histograms.
18. Pytest + coverage gate: PASS  
Proof: `pytest` with coverage threshold enforced.
19. `ruff` and `mypy` clean: PASS  
Proof: `ruff check .`, `mypy src`.
20. CI green on main: PENDING  
Proof: latest GitHub Actions run all green.
21. Object-store swap by env var: PARTIAL  
Seam implemented (`local`/`minio`), formal live demo swap pending.

## Close-remaining-gaps commands only

```bash
# 2 lite profile
make demo-lite

# 8 payload-too-large (example 25MB file)
mkfile 25m /tmp/large.bin
API_KEY=$(grep '^API_KEY=' .env | cut -d= -f2)
curl -s -o /tmp/large.out -w '%{http_code}' -X POST http://localhost:8000/api/v1/uploads \
  -H "Authorization: Bearer $API_KEY" \
  -F "file=@/tmp/large.bin;filename=large.jpg"

# 11 claude invalid-key path
AI_PROVIDER=claude ANTHROPIC_API_KEY=invalid docker compose up -d --build api worker
# then submit upload and check job error payload

# 20 CI status
gh run list --limit 5

# 21 object-store swap (local -> minio)
# set OBJECT_STORE_BACKEND=minio and verify upload/report flow
```
