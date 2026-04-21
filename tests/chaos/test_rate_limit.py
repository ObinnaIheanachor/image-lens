from __future__ import annotations

from pathlib import Path

from src.config import settings


def test_upload_rate_limit_trips_after_threshold(client, monkeypatch) -> None:
    monkeypatch.setattr("src.security.rate_limit._backend", None)

    class _StubLimiter:
        def __init__(self) -> None:
            self.calls = 0

        def allow(self, key: str, limit: int, window_seconds: int) -> bool:
            self.calls += 1
            return self.calls <= 2

    stub = _StubLimiter()
    monkeypatch.setattr("src.security.rate_limit._backend", stub)
    monkeypatch.setattr(settings, "rate_limit_enabled", True)
    monkeypatch.setattr(settings, "rate_limit_uploads_per_minute", 2)

    headers = {"Authorization": f"Bearer {settings.api_key}"}
    payload = Path("tests/fixtures/valid.jpg").read_bytes()

    ok1 = client.post(
        "/api/v1/uploads",
        headers=headers,
        files={"file": ("a.jpg", payload, "image/jpeg")},
    )
    assert ok1.status_code == 202

    ok2 = client.post(
        "/api/v1/uploads",
        headers=headers,
        files={"file": ("b.jpg", payload, "image/jpeg")},
    )
    assert ok2.status_code == 202

    blocked = client.post(
        "/api/v1/uploads",
        headers=headers,
        files={"file": ("c.jpg", payload, "image/jpeg")},
    )
    assert blocked.status_code == 429
    assert blocked.json()["detail"] == "rate_limited"
