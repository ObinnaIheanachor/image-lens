from __future__ import annotations

from src.analyzers.claude.analyzer import ClaudeVisionAnalyzer
from src.config import settings


class _Resp:
    def __init__(self, status_code: int, payload: dict) -> None:
        self.status_code = status_code
        self._payload = payload
        self.text = str(payload)

    def json(self) -> dict:
        return self._payload


def test_claude_analyzer_parses_fenced_json(monkeypatch) -> None:
    monkeypatch.setattr(settings, "anthropic_api_key", "test-key")
    analyzer = ClaudeVisionAnalyzer()

    payload = {
        "content": [
            {
                "type": "text",
                "text": (
                    "```json\n"
                    '{"summary":"Readable summary","tags":["engineering","connector"],"confidence":0.91}\n'
                    "```"
                ),
            }
        ]
    }
    monkeypatch.setattr(
        "src.analyzers.claude.analyzer.requests.post",
        lambda *args, **kwargs: _Resp(200, payload),
    )

    result = analyzer.analyze(b"abc", "image/jpeg")
    assert result.summary == "Readable summary"
    assert result.tags == ["engineering", "connector"]
    assert result.confidence == 0.91
    assert result.analyzer_version == analyzer.version


def test_claude_analyzer_falls_back_for_unstructured_text(monkeypatch) -> None:
    monkeypatch.setattr(settings, "anthropic_api_key", "test-key")
    analyzer = ClaudeVisionAnalyzer()

    payload = {
        "content": [
            {
                "type": "text",
                "text": "This is freeform prose, not JSON.",
            }
        ]
    }
    monkeypatch.setattr(
        "src.analyzers.claude.analyzer.requests.post",
        lambda *args, **kwargs: _Resp(200, payload),
    )

    result = analyzer.analyze(b"abc", "image/jpeg")
    assert result.summary.startswith("This is freeform prose")
    assert result.tags == ["unstructured"]
    assert result.confidence == 0.5
