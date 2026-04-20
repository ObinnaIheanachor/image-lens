from __future__ import annotations

import json
from pathlib import Path

import pytest
import requests
import vcr

CASSETTE = Path("tests/contract/cassettes/claude_live_once.yaml")


def test_claude_contract_via_vcr() -> None:
    if not CASSETTE.exists():
        pytest.skip("Cassette missing. Record once via scripts/validate_claude_and_record_vcr.py")

    recorder = vcr.VCR(
        cassette_library_dir=str(CASSETTE.parent),
        filter_headers=["x-api-key", "authorization"],
        record_mode="none",
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
                "x-api-key": "DUMMY",
                "anthropic-version": "2023-06-01",
                "content-type": "application/json",
            },
            data=json.dumps(payload),
            timeout=30,
        )

    assert resp.status_code == 200
    data = resp.json()
    assert "content" in data
