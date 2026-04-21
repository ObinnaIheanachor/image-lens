from __future__ import annotations

import json
import os
import time
from pathlib import Path

import requests


def poll_job(base: str, headers: dict[str, str], job_id: str, want: str, timeout: float = 20.0) -> dict:
    deadline = time.time() + timeout
    while time.time() < deadline:
        r = requests.get(f"{base}/api/v1/jobs/{job_id}", headers=headers, timeout=10)
        r.raise_for_status()
        p = r.json()
        if p["status"] == want:
            return p
        time.sleep(0.3)
    raise RuntimeError(f"timeout waiting for {job_id} -> {want}")


def main() -> None:
    base = os.getenv("API_BASE_URL", "http://localhost:8000")
    frontend = os.getenv("FRONTEND_BASE_URL", "http://localhost:5173")
    api_key = os.getenv("API_KEY")
    if not api_key and Path(".env").exists():
        for line in Path(".env").read_text().splitlines():
            if line.startswith("API_KEY="):
                api_key = line.split("=", 1)[1].strip()
                break
    if not api_key:
        raise SystemExit("API_KEY missing")

    headers = {"Authorization": f"Bearer {api_key}"}
    fixture = Path("tests/fixtures/valid.jpg")

    # Core probes
    assert requests.get(f"{base}/api/v1/healthz", timeout=10).status_code == 200
    assert requests.get(f"{base}/api/v1/readyz", timeout=10).status_code == 200
    assert requests.get(frontend, timeout=10).status_code == 200
    assert requests.get(f"{frontend}/?mode=dev", timeout=10).status_code == 200

    # Scenario A: happy path
    with fixture.open("rb") as f:
        up = requests.post(f"{base}/api/v1/uploads", headers=headers, files={"file": ("a.jpg", f, "image/jpeg")}, timeout=20)
    up.raise_for_status()
    job_id = up.json()["job_id"]
    done = poll_job(base, headers, job_id, "done")
    report_id = done["report_id"]
    assert report_id

    # report formats
    for accept, expect in [
        ("application/json", 200),
        ("text/markdown", 200),
        ("text/html", 200),
        ("application/pdf", 200),
    ]:
        rr = requests.get(f"{base}/api/v1/reports/{report_id}", headers={**headers, "Accept": accept}, timeout=20)
        assert rr.status_code == expect

    # Scenario C idempotency
    idem_h = {**headers, "Idempotency-Key": "dryrun-idem-1"}
    with fixture.open("rb") as f:
        a = requests.post(f"{base}/api/v1/uploads", headers=idem_h, files={"file": ("id1.jpg", f, "image/jpeg")}, timeout=20)
    a.raise_for_status()
    with fixture.open("rb") as f:
        b = requests.post(f"{base}/api/v1/uploads", headers=idem_h, files={"file": ("id2.jpg", f, "image/jpeg")}, timeout=20)
    b.raise_for_status()
    assert a.json()["job_id"] == b.json()["job_id"]

    # Scenario D retry
    with fixture.open("rb") as f:
        r = requests.post(
            f"{base}/api/v1/uploads",
            headers=headers,
            data={"metadata": json.dumps({"force_fail_once": True})},
            files={"file": ("retry.jpg", f, "image/jpeg")},
            timeout=20,
        )
    r.raise_for_status()
    rj = r.json()["job_id"]
    poll_job(base, headers, rj, "failed")
    retry = requests.post(f"{base}/api/v1/jobs/{rj}/retry", headers=headers, timeout=10)
    retry.raise_for_status()
    poll_job(base, headers, rj, "done")

    # Scenario E batch
    files = []
    for i in range(5):
        files.append(("files[]", (f"b{i}.jpg", fixture.read_bytes(), "image/jpeg")))
    batch = requests.post(f"{base}/api/v1/uploads", headers=headers, files=files, timeout=30)
    batch.raise_for_status()
    bpayload = batch.json()
    assert isinstance(bpayload, list) and len(bpayload) == 5

    # Scenario F webhook
    with fixture.open("rb") as f:
        w = requests.post(
            f"{base}/api/v1/uploads",
            headers=headers,
            data={"webhook_url": "http://host.docker.internal:8888/hook"},
            files={"file": ("wh.jpg", f, "image/jpeg")},
            timeout=20,
        )
    w.raise_for_status()

    # Scenario G delete
    del_job = bpayload[0]["job_id"]
    d = requests.delete(f"{base}/api/v1/jobs/{del_job}", headers=headers, timeout=10)
    d.raise_for_status()

    print("dry-run ok")


if __name__ == "__main__":
    main()
