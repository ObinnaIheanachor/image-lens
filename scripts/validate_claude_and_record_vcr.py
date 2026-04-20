from __future__ import annotations

import json
import os
from pathlib import Path

import requests
import vcr

CASSETTE = Path("tests/contract/cassettes/claude_live_once.yaml")


def _api_key() -> str:
    key = os.getenv("ANTHROPIC_API_KEY", "").strip()
    if key:
        return key
    env_path = Path(".env")
    if env_path.exists():
        for line in env_path.read_text().splitlines():
            if line.startswith("ANTHROPIC_API_KEY="):
                return line.split("=", 1)[1].strip()
    return ""


def main() -> None:
    key = _api_key()
    if not key:
        raise SystemExit("ANTHROPIC_API_KEY missing. Set env var or .env.")

    CASSETTE.parent.mkdir(parents=True, exist_ok=True)

    recorder = vcr.VCR(
        cassette_library_dir=str(CASSETTE.parent),
        filter_headers=["x-api-key", "authorization"],
        record_mode="once",
        decode_compressed_response=True,
    )

    payload = {
        "model": "claude-sonnet-4-20250514",
        "max_tokens": 80,
        "messages": [{"role": "user", "content": "Return JSON: {\"ok\": true}"}],
    }

    with recorder.use_cassette(CASSETTE.name):
        resp = requests.post(
            "https://api.anthropic.com/v1/messages",
            headers={
                "x-api-key": key,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json",
            },
            data=json.dumps(payload),
            timeout=30,
        )
        if resp.status_code >= 400:
            raise SystemExit(f"Claude live validation failed: {resp.status_code} {resp.text}")

    print(f"Recorded cassette: {CASSETTE}")


if __name__ == "__main__":
    main()
