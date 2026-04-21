from __future__ import annotations

from typing import Protocol

from src.domain.schemas import AnalysisResult


class VisionAnalyzer(Protocol):
    version: str

    def analyze(self, image_bytes: bytes, mime: str) -> AnalysisResult:
        ...
