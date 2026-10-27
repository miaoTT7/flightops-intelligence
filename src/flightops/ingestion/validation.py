"""Streaming inspection and validation of BTS CSV content."""

from __future__ import annotations

import csv
import io
from dataclasses import dataclass

from flightops.common.checksums import stream_sha256
from flightops.ingestion.errors import IngestionError
from flightops.ingestion.schema import SCHEMA_FINGERPRINT, SOURCE_COLUMNS
from flightops.ingestion.source import SourceInput


@dataclass(frozen=True)
class Inspection:
    source_year: int
    source_month: int
    row_count: int
    csv_sha256: str
    csv_size_bytes: int
    schema_fingerprint: str
    has_empty_trailing_column: bool


def normalize_header(header: list[str]) -> tuple[list[str], bool]:
    """Accept the BTS trailing empty column, but no unknown schema drift."""

    if header == SOURCE_COLUMNS:
        return header, False
    if header == [*SOURCE_COLUMNS, ""]:
        return header[:-1], True
    missing = sorted(set(SOURCE_COLUMNS).difference(header))
    unexpected = sorted(set(header).difference(SOURCE_COLUMNS).difference({""}))
    raise IngestionError(
        "SCHEMA_MISMATCH",
        f"Missing columns={missing}; unexpected columns={unexpected}; "
        f"expected {len(SOURCE_COLUMNS)}, received {len(header)}",
        stage="validation",
    )


def iter_validated_rows(
    source: SourceInput,
    *,
    expected_year: int | None = None,
    expected_month: int | None = None,
):
    """Yield validated source rows without retaining the dataset in memory."""

    with source.open_csv_binary() as binary:
        with io.TextIOWrapper(binary, encoding="utf-8-sig", newline="") as text:
            reader = csv.reader(text)
            try:
                raw_header = next(reader)
            except StopIteration as exc:
                raise IngestionError("EMPTY_FILE", source.path.name, stage="validation") from exc
            _, trailing = normalize_header(raw_header)
            width = len(raw_header)
            year_index = SOURCE_COLUMNS.index("Year")
            month_index = SOURCE_COLUMNS.index("Month")
            for data_row_number, raw_row in enumerate(reader, start=1):
                if len(raw_row) != width:
                    raise IngestionError(
                        "ROW_WIDTH_MISMATCH",
                        f"Expected {width} fields, received {len(raw_row)}",
                        stage="validation",
                        row_number=data_row_number,
                    )
                if trailing:
                    if raw_row[-1] != "":
                        raise IngestionError(
                            "NONEMPTY_TRAILING_COLUMN",
                            "The unnamed trailing column contains data",
                            stage="validation",
                            row_number=data_row_number,
                        )
                    row = raw_row[:-1]
                else:
                    row = raw_row
                try:
                    year = int(row[year_index])
                    month = int(row[month_index])
                except ValueError as exc:
                    raise IngestionError(
                        "INVALID_PERIOD", "Year and Month must be integers",
                        stage="validation", row_number=data_row_number,
                    ) from exc
                if not 1 <= month <= 12:
                    raise IngestionError(
                        "INVALID_PERIOD", f"Invalid month {month}",
                        stage="validation", row_number=data_row_number,
                    )
                if expected_year is not None and (year, month) != (
                    expected_year,
                    expected_month,
                ):
                    raise IngestionError(
                        "SOURCE_MONTH_MISMATCH",
                        f"Expected {expected_year}-{expected_month:02d}, observed {year}-{month:02d}",
                        stage="validation",
                        row_number=data_row_number,
                    )
                yield row


def inspect_source(source: SourceInput) -> Inspection:
    """Hash and fully validate one CSV using bounded memory."""

    with source.open_csv_binary() as binary:
        csv_sha, csv_size = stream_sha256(binary)

    row_count = 0
    source_year: int | None = None
    source_month: int | None = None
    with source.open_csv_binary() as binary:
        with io.TextIOWrapper(binary, encoding="utf-8-sig", newline="") as text:
            reader = csv.reader(text)
            try:
                raw_header = next(reader)
            except StopIteration as exc:
                raise IngestionError("EMPTY_FILE", source.path.name, stage="validation") from exc
            _, trailing = normalize_header(raw_header)
            width = len(raw_header)
            year_index = SOURCE_COLUMNS.index("Year")
            month_index = SOURCE_COLUMNS.index("Month")
            for row_count, raw_row in enumerate(reader, start=1):
                if len(raw_row) != width:
                    raise IngestionError(
                        "ROW_WIDTH_MISMATCH", f"Expected {width} fields, received {len(raw_row)}",
                        stage="validation", row_number=row_count,
                    )
                if trailing:
                    if raw_row[-1] != "":
                        raise IngestionError(
                            "NONEMPTY_TRAILING_COLUMN", "The unnamed trailing column contains data",
                            stage="validation", row_number=row_count,
                        )
                    raw_row = raw_row[:-1]
                try:
                    year = int(raw_row[year_index])
                    month = int(raw_row[month_index])
                except ValueError as exc:
                    raise IngestionError(
                        "INVALID_PERIOD", "Year and Month must be integers",
                        stage="validation", row_number=row_count,
                    ) from exc
                if not 1 <= month <= 12:
                    raise IngestionError(
                        "INVALID_PERIOD", f"Invalid month {month}",
                        stage="validation", row_number=row_count,
                    )
                if source_year is None:
                    source_year, source_month = year, month
                elif (year, month) != (source_year, source_month):
                    raise IngestionError(
                        "SOURCE_MONTH_MISMATCH",
                        f"Expected {source_year}-{source_month:02d}, observed {year}-{month:02d}",
                        stage="validation", row_number=row_count,
                    )
    if row_count == 0 or source_year is None or source_month is None:
        raise IngestionError("NO_DATA_ROWS", source.path.name, stage="validation")
    return Inspection(
        source_year=source_year,
        source_month=source_month,
        row_count=row_count,
        csv_sha256=csv_sha,
        csv_size_bytes=csv_size,
        schema_fingerprint=SCHEMA_FINGERPRINT,
        has_empty_trailing_column=trailing,
    )
