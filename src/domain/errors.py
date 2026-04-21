from __future__ import annotations

from dataclasses import dataclass


@dataclass
class AppError(Exception):
    status_code: int
    code: str
    message: str


class ValidationError(AppError):
    def __init__(self, code: str, message: str, status_code: int = 400) -> None:
        super().__init__(status_code=status_code, code=code, message=message)


class AnalyzerError(AppError):
    def __init__(self, code: str, message: str, status_code: int = 502) -> None:
        super().__init__(status_code=status_code, code=code, message=message)
