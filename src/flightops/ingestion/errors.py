"""Stable, user-facing ingestion errors."""

from __future__ import annotations


class IngestionError(Exception):
    """An expected ingestion failure with a stable code and stage."""

    def __init__(
        self,
        code: str,
        message: str,
        *,
        stage: str,
        row_number: int | None = None,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.stage = stage
        self.row_number = row_number

    def __str__(self) -> str:
        location = f" at data row {self.row_number}" if self.row_number else ""
        return f"[{self.stage}:{self.code}]{location} {super().__str__()}"

