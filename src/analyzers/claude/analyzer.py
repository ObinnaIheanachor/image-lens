from __future__ import annotations

import json

import requests

from src.config import settings
from src.domain.errors import AnalyzerError
from src.domain.schemas import AnalysisResult


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
                                "Return compact JSON with keys: summary (string), tags (array of strings), "
                                "confidence (0..1)."
                            ),
                        },
                    ],
                }
            ],
        }

        # Anthropic expects base64; convert hex payload to base64 bytes without external deps.
        # requests/json handles content body, endpoint validates auth and model path.
        import base64

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

        try:
            parsed = json.loads(text)
        except Exception:
            # Fallback when model returns prose.
            parsed = {"summary": text[:500], "tags": ["unstructured"], "confidence": 0.5}

        return AnalysisResult(
            summary=str(parsed.get("summary", "No summary")),
            tags=[str(t) for t in parsed.get("tags", ["unknown"])][:10],
            confidence=float(parsed.get("confidence", 0.5)),
            analyzer_version=self.version,
        )
