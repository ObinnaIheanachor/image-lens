from __future__ import annotations

import hashlib

from src.domain.schemas import AnalysisResult


class MockAnalyzer:
    version = "mock-v1"

    def analyze(self, image_bytes: bytes, mime: str) -> AnalysisResult:
        digest = hashlib.sha256(image_bytes).hexdigest()
        seed = int(digest[:8], 16)
        confidence = round(0.75 + ((seed % 20) / 100), 2)
        tags = ["image", "inspection", f"bucket-{seed % 5}", mime]
        summary = f"Deterministic mock analysis complete for hash prefix {digest[:12]}."
        return AnalysisResult(
            summary=summary,
            tags=tags,
            confidence=min(confidence, 0.99),
            analyzer_version=self.version,
        )
