from __future__ import annotations

import json
import threading
import time
from http.server import BaseHTTPRequestHandler, HTTPServer
from io import BytesIO

from PIL import Image

from src.config import settings


def _make_jpeg(color: tuple[int, int, int]) -> bytes:
    img = Image.new("RGB", (32, 32), color)
    buffer = BytesIO()
    img.save(buffer, format="JPEG")
    return buffer.getvalue()


def _auth_headers() -> dict[str, str]:
    return {"Authorization": f"Bearer {settings.api_key}"}


def _poll_job_until(client, job_id: str, status: str, timeout_s: float = 8.0) -> dict:
    deadline = time.time() + timeout_s
    while time.time() < deadline:
        resp = client.get(f"/api/v1/jobs/{job_id}", headers=_auth_headers())
        assert resp.status_code == 200
        payload = resp.json()
        if payload["status"] == status:
            return payload
        time.sleep(0.1)
    raise AssertionError(f"job {job_id} did not reach {status}")


def test_idempotency_key_same_file_same_job_and_conflict_on_different_file(client) -> None:
    jpeg_a = _make_jpeg((255, 0, 0))
    jpeg_b = _make_jpeg((0, 0, 255))

    headers = {**_auth_headers(), "Idempotency-Key": "idem-key-1"}

    first = client.post(
        "/api/v1/uploads",
        headers=headers,
        files={"file": ("a.jpg", jpeg_a, "image/jpeg")},
    )
    assert first.status_code == 202
    first_job = first.json()["job_id"]

    second = client.post(
        "/api/v1/uploads",
        headers=headers,
        files={"file": ("a-again.jpg", jpeg_a, "image/jpeg")},
    )
    assert second.status_code == 202
    assert second.json()["job_id"] == first_job

    conflict = client.post(
        "/api/v1/uploads",
        headers=headers,
        files={"file": ("b.jpg", jpeg_b, "image/jpeg")},
    )
    assert conflict.status_code == 409
    assert conflict.json()["detail"] == "idempotency_conflict"


def test_batch_upload_creates_five_jobs(client) -> None:
    files_payload = []
    for idx in range(5):
        jpeg = _make_jpeg((idx * 30, 20, 120))
        files_payload.append(("files[]", (f"img-{idx}.jpg", jpeg, "image/jpeg")))

    resp = client.post("/api/v1/uploads", headers=_auth_headers(), files=files_payload)
    assert resp.status_code == 202

    payload = resp.json()
    assert isinstance(payload, list)
    assert len(payload) == 5

    for item in payload:
        assert item["job_id"].startswith("job_")
        _poll_job_until(client, item["job_id"], "done")


def test_report_formats_json_markdown_html_pdf(client, monkeypatch) -> None:
    upload = client.post(
        "/api/v1/uploads",
        headers=_auth_headers(),
        files={"file": ("x.jpg", _make_jpeg((10, 130, 80)), "image/jpeg")},
    )
    assert upload.status_code == 202
    job_id = upload.json()["job_id"]

    job_payload = _poll_job_until(client, job_id, "done")
    report_id = job_payload["report_id"]

    monkeypatch.setattr("src.api.routes.render_pdf", lambda _ctx: b"%PDF-1.4 test")

    j = client.get(f"/api/v1/reports/{report_id}", headers={**_auth_headers(), "Accept": "application/json"})
    assert j.status_code == 200
    assert j.headers["content-type"].startswith("application/json")

    md = client.get(f"/api/v1/reports/{report_id}", headers={**_auth_headers(), "Accept": "text/markdown"})
    assert md.status_code == 200
    assert md.headers["content-type"].startswith("text/markdown")
    assert "# Image Insight Report" in md.text

    html = client.get(f"/api/v1/reports/{report_id}", headers={**_auth_headers(), "Accept": "text/html"})
    assert html.status_code == 200
    assert html.headers["content-type"].startswith("text/html")
    assert "<html" in html.text.lower()

    pdf = client.get(f"/api/v1/reports/{report_id}", headers={**_auth_headers(), "Accept": "application/pdf"})
    assert pdf.status_code == 200
    assert pdf.headers["content-type"].startswith("application/pdf")
    assert pdf.content.startswith(b"%PDF")


def test_retry_and_webhook_and_readiness_degradation(client, monkeypatch) -> None:
    received: list[dict] = []

    class Handler(BaseHTTPRequestHandler):
        def do_POST(self):  # noqa: N802
            length = int(self.headers.get("content-length", "0"))
            payload = self.rfile.read(length)
            received.append(json.loads(payload.decode("utf-8")))
            self.send_response(200)
            self.end_headers()

        def log_message(self, _format, *_args):
            return

    server = HTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()

    try:
        webhook_url = f"http://127.0.0.1:{server.server_port}/hook"
        upload = client.post(
            "/api/v1/uploads",
            headers=_auth_headers(),
            data={"metadata": json.dumps({"force_fail_once": True}), "webhook_url": webhook_url},
            files={"file": ("x.jpg", _make_jpeg((200, 80, 80)), "image/jpeg")},
        )
        assert upload.status_code == 202
        job_id = upload.json()["job_id"]

        _poll_job_until(client, job_id, "failed")

        retry = client.post(f"/api/v1/jobs/{job_id}/retry", headers=_auth_headers())
        assert retry.status_code == 200
        assert retry.json()["status"] in {"queued", "done"}

        done = retry.json() if retry.json()["status"] == "done" else _poll_job_until(client, job_id, "done")
        assert done["report_id"]

        deadline = time.time() + 5
        while time.time() < deadline and not received:
            time.sleep(0.1)
        assert received, "webhook payload not received"
        assert received[0]["job_id"] == job_id
        assert received[0]["status"] == "done"

        monkeypatch.setattr("src.api.routes.queue_backend.is_ready", lambda: False)
        degraded = client.get("/api/v1/readyz")
        assert degraded.status_code == 503
        body = degraded.json()["detail"]
        assert body["status"] == "degraded"
        assert body["dependencies"]["queue"] == "down"
    finally:
        server.shutdown()
        server.server_close()


def test_metrics_endpoint_and_fake_pdf_rejection(client) -> None:
    metrics = client.get("/api/v1/metrics")
    assert metrics.status_code == 200
    assert "image_insight_http_requests_total" in metrics.text
    assert "image_intel_analysis_duration_seconds" in metrics.text
    assert "image_intel_analysis_failures_total" in metrics.text
    assert "image_intel_queue_depth" in metrics.text
    assert "image_intel_jobs_in_flight" in metrics.text
    assert "image_intel_circuit_breaker_state" in metrics.text
    assert "image_intel_webhook_delivery_total" in metrics.text
    assert "image_intel_uploads_total" in metrics.text

    fake_pdf_as_jpg = b"%PDF-1.7 fake"
    resp = client.post(
        "/api/v1/uploads",
        headers=_auth_headers(),
        files={"file": ("fake.jpg", fake_pdf_as_jpg, "image/jpeg")},
    )
    assert resp.status_code == 415
    assert resp.json()["detail"] == "unsupported_media_type"
