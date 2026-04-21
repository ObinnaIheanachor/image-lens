from src.analyzers.mock import MockAnalyzer


def test_mock_analyzer_is_deterministic() -> None:
    analyzer = MockAnalyzer()
    data = b"abc123"
    result_a = analyzer.analyze(data, "image/jpeg")
    result_b = analyzer.analyze(data, "image/jpeg")

    assert result_a == result_b
    assert result_a.analyzer_version == "mock-v1"
