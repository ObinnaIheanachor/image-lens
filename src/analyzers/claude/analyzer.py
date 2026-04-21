from __future__ import annotations

import base64
import json
import re
from typing import Any

import requests

from src.config import settings
from src.domain.errors import AnalyzerError
from src.domain.schemas import AnalysisResult


_FENCED_JSON_RE = re.compile(r"```(?:json)?\s*(.*?)```", re.IGNORECASE | re.DOTALL)


def _extract_json_candidate(text: str) -> Any | None:
    cleaned = text.strip()
    if not cleaned:
        return None

    # First try direct parse.
    try:
        return json.loads(cleaned)
    except Exception:
        pass

    # Then parse fenced JSON blocks.
    fenced_match = _FENCED_JSON_RE.search(cleaned)
    if fenced_match:
        fenced_body = fenced_match.group(1).strip()
        try:
            return json.loads(fenced_body)
        except Exception:
            pass

    # Finally, decode first JSON object/array embedded in prose.
    decoder = json.JSONDecoder()
    for idx, ch in enumerate(cleaned):
        if ch not in "{[":
            continue
        try:
            parsed, _ = decoder.raw_decode(cleaned[idx:])
            return parsed
        except Exception:
            continue
    return None


def _normalize_result(parsed: Any, fallback_text: str, version: str) -> AnalysisResult:
    if not isinstance(parsed, dict):
        parsed = {}

    summary = parsed.get("summary")
    tags = parsed.get("tags")
    confidence = parsed.get("confidence")

    final_summary = str(summary).strip() if summary is not None else ""
    if not final_summary:
        final_summary = (fallback_text.strip() or "No summary")[:500]

    final_tags: list[str] = []
    if isinstance(tags, list):
        final_tags = [str(tag).strip() for tag in tags if str(tag).strip()][:10]
    if not final_tags:
        final_tags = ["unstructured"]

    try:
        final_confidence = float(confidence)
    except Exception:
        final_confidence = 0.5
    final_confidence = min(max(final_confidence, 0.0), 1.0)

    return AnalysisResult(
        summary=final_summary,
        tags=final_tags,
        confidence=final_confidence,
        analyzer_version=version,
    )


class ClaudeVisionAnalyzer:
    version = "claude-sonnet-4-20250514-v1"

    def analyze(self, image_bytes: bytes, mime: str) -> AnalysisResult:
        if not settings.anthropic_api_key:
            raise AnalyzerError("analyzer_auth_failed", "ANTHROPIC_API_KEY not configured", status_code=401)

        payload: dict[str, object] = {
            "model": settings.claude_model,
            "max_tokens": 300,
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image",
                            "source": {
                                "type": "base64",
                                "media_type": mime,
                                "data": image_bytes.hex(),
                            },
                        },
                        {
                            "type": "text",
                            "text": (
                                "Return ONLY a raw JSON object with keys: summary (string), "
                                "tags (array of strings), confidence (number 0..1). "
                                "Do not include markdown fences or commentary."
                            ),
                        },
                    ],
                }
            ],
        }

        payload["messages"][0]["content"][0]["source"]["data"] = base64.b64encode(image_bytes).decode("ascii")  # type: ignore[index]

        try:
            resp = requests.post(
                "https://api.anthropic.com/v1/messages",
                headers={
                    "x-api-key": settings.anthropic_api_key,
                    "anthropic-version": "2023-06-01",
                    "content-type": "application/json",
                },
                data=json.dumps(payload),
                timeout=30,
            )
        except Exception as exc:
            raise AnalyzerError("analyzer_timeout", str(exc), status_code=504) from exc

        if resp.status_code in (401, 403):
            raise AnalyzerError("analyzer_auth_failed", resp.text, status_code=401)
        if resp.status_code >= 500:
            raise AnalyzerError("analyzer_upstream_error", resp.text, status_code=502)
        if resp.status_code >= 400:
            raise AnalyzerError("analyzer_bad_request", resp.text, status_code=400)

        data = resp.json()
        text_blocks = [c.get("text", "") for c in data.get("content", []) if c.get("type") == "text"]
        text = "\n".join(text_blocks).strip()
        parsed = _extract_json_candidate(text)

        return _normalize_result(parsed, text, self.version)
