from __future__ import annotations

import json
import os
import time
from pathlib import Path

import requests


def main() -> None:
    base = os.getenv("API_BASE_URL", "http://localhost:8000")
    api_key = os.getenv("API_KEY")
    if not api_key:
        env_path = Path(".env")
        if env_path.exists():
            for line in env_path.read_text().splitlines():
                if line.startswith("API_KEY="):
                    api_key = line.split("=", 1)[1].strip()
                    break
    if not api_key:
        raise SystemExit("API_KEY missing. Set env var or .env file.")

    fixture = Path("tests/fixtures/valid.jpg")
    if not fixture.exists():
        raise SystemExit("Missing tests/fixtures/valid.jpg")

    headers = {"Authorization": f"Bearer {api_key}"}
    seeded = []

    for idx in range(5):
        with fixture.open("rb") as f:
            resp = requests.post(
                f"{base}/api/v1/uploads",
                headers=headers,
                files={"file": (f"seed-{idx}.jpg", f, "image/jpeg")},
                timeout=20,
            )
        resp.raise_for_status()
        payload = resp.json()
        job_id = payload["job_id"]

        report_id = None
        deadline = time.time() + 20
        while time.time() < deadline:
            job = requests.get(f"{base}/api/v1/jobs/{job_id}", headers=headers, timeout=10)
            job.raise_for_status()
            p = job.json()
            if p["status"] == "done":
                report_id = p["report_id"]
                break
            if p["status"] == "failed":
                raise RuntimeError(f"seed job failed: {job_id} -> {p}")
            time.sleep(0.3)

        if not report_id:
            raise RuntimeError(f"seed job timeout: {job_id}")

        seeded.append({"job_id": job_id, "report_id": report_id})

    print(json.dumps({"seeded": seeded}, indent=2))


if __name__ == "__main__":
    main()
