from __future__ import annotations

import json
from urllib.parse import urlparse

import requests

from src.config import settings


def is_valid_webhook_url(url: str) -> bool:
    try:
        parsed = urlparse(url)
    except Exception:
        return False
    if parsed.scheme not in {"http", "https"}:
        return False
    if not parsed.netloc:
        return False
    if not settings.allow_private_webhooks and parsed.hostname in {"localhost", "127.0.0.1"}:
        return False
    return True


def dispatch_webhook(url: str, payload: dict) -> tuple[bool, str | None]:
    try:
        response = requests.post(
            url,
            data=json.dumps(payload),
            headers={"content-type": "application/json"},
            timeout=settings.webhook_timeout_seconds,
        )
        if 200 <= response.status_code < 300:
            return True, None
        return False, f"webhook_http_{response.status_code}"
    except Exception as exc:
        return False, str(exc)
