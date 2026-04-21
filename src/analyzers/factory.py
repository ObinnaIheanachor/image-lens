from __future__ import annotations

from src.analyzers.mock import MockAnalyzer
from src.analyzers.protocol import VisionAnalyzer
from src.config import settings


def create_analyzer() -> VisionAnalyzer:
    if settings.ai_provider == "claude":
        from src.analyzers.claude.analyzer import ClaudeVisionAnalyzer

        return ClaudeVisionAnalyzer()
    return MockAnalyzer()
