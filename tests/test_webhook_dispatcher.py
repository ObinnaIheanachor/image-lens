from __future__ import annotations

import requests

from src.config import settings
from src.services.webhook_dispatcher import dispatch_webhook, is_valid_webhook_url


class _Resp:
    def __init__(self, status_code: int) -> None:
        self.status_code = status_code


def test_is_valid_webhook_url_respects_private_host_setting(monkeypatch) -> None:
    monkeypatch.setattr(settings, "allow_private_webhooks", False)
    assert not is_valid_webhook_url("http://localhost:8080/hook")
    assert not is_valid_webhook_url("http://127.0.0.1:8080/hook")
    assert is_valid_webhook_url("https://webhook.site/abc")

    monkeypatch.setattr(settings, "allow_private_webhooks", True)
    assert is_valid_webhook_url("http://localhost:8080/hook")


def test_dispatch_webhook_success_and_http_failure(monkeypatch) -> None:
    monkeypatch.setattr("src.services.webhook_dispatcher.requests.post", lambda *args, **kwargs: _Resp(200))
    ok, error = dispatch_webhook("https://example.com/hook", {"job_id": "job_1"})
    assert ok is True
    assert error is None

    monkeypatch.setattr("src.services.webhook_dispatcher.requests.post", lambda *args, **kwargs: _Resp(503))
    ok, error = dispatch_webhook("https://example.com/hook", {"job_id": "job_1"})
    assert ok is False
    assert error == "webhook_http_503"


def test_dispatch_webhook_exception(monkeypatch) -> None:
    def _boom(*_args, **_kwargs):
        raise requests.RequestException("network down")

    monkeypatch.setattr("src.services.webhook_dispatcher.requests.post", _boom)
    ok, error = dispatch_webhook("https://example.com/hook", {"job_id": "job_1"})
    assert ok is False
    assert "network down" in (error or "")
