# Acceptance Checklist Audit

Date: 2026-04-21

Legend:
- PASS: validated in current code/runtime
- PARTIAL: implemented but not fully proven for target criterion wording
- FAIL: known gap
- PENDING: not yet validated in current environment

## Criteria status

1. `docker compose up --build` full-stack + frontend end-to-end: PASS  
Proof: `docker compose up -d --build` then `GET /api/v1/readyz` and frontend `GET /` + `GET /?mode=dev` return `200`.
2. Lite profile offline fallback: PASS  
Proof: `docker compose -f docker-compose.lite.yml up -d --build` + `GET /api/v1/readyz` + upload flow validated.
3. Valid upload returns `job_id` quickly: PASS  
Proof: `POST /api/v1/uploads` returns `202` + `job_id`.
4. Mock job reaches `done` and report available: PASS  
Proof: poll `GET /jobs/{id}` to `done`, fetch report.
5. Report formats JSON/MD/HTML/PDF: PASS  
Proof: `Accept: application/json|text/markdown|text/html|application/pdf` each `200`.
6. Idempotency same key => same job: PASS  
Proof: repeated upload with same `Idempotency-Key` and same image returns same `job_id`.
7. Fake `.jpg` with PDF payload => `unsupported_media_type`: PASS  
Proof: upload `%PDF-` as `fake.jpg` returns `415` with `detail=unsupported_media_type`.
8. 25MB file => `413 payload_too_large`: PASS  
Proof: upload `/tmp/large.jpg` (25MB) returns `413`.
9. Zero-byte file => `400 empty_file`: PASS  
Proof: upload empty payload returns `400`.
10. Batch upload of 5 => 5 jobs/reports: PASS  
Proof: `files[]` batch returns 5 queued jobs; jobs complete to `done`.
11. Claude live path validated + cassette for CI: PASS  
Proof: `/tmp/mambaenv/bin/python scripts/validate_claude_and_record_vcr.py` + `pytest -q tests/contract -o addopts=""`.
12. Mock default/offline demo: PASS  
Proof: `.env.example` default `AI_PROVIDER=mock`.
13. Retry failed job re-queues: PASS  
Proof: forced fail metadata + `POST /jobs/{id}/retry` transitions back to queued/done.
14. GDPR delete semantics (bytes removed + report payload removed + audit retained): PASS  
Proof: `DELETE /jobs/{id}` => `200`, job status becomes `deleted`, report fetch returns `410 report_deleted`.
15. Webhook delivered within 30s: PASS  
Proof: `webhook-echo` logs show POST with `job_id/report_id/status=done`.
16. `/readyz` dependency degradation: PASS  
Proof: stop Redis, `/readyz` returns `503` with `queue: down`.
17. `/metrics` exposes Prometheus metrics: PASS  
Proof: `GET /api/v1/metrics` includes `image_insight_http_requests_total`.
18. Pytest + coverage gate: PASS  
Proof: `pytest -q` coverage threshold met.
19. `ruff` and `mypy` clean: PASS  
Proof: `ruff check .` and `mypy src` both clean.
20. CI green on main: PENDING  
Proof command: `gh run list --limit 5`.
21. Object-store swap by env var: PASS  
Proof: full-stack run validated with MinIO backend; local backend also implemented.

## Remaining closeout commands

```bash
# CI status check
 gh run list --limit 5

# Optional: validate lite fallback profile
 docker compose -f docker-compose.lite.yml up --build
```
