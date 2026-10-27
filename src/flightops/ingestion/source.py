"""Input discovery and safe access to CSV content inside files or ZIPs."""

from __future__ import annotations

from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import BinaryIO, Iterator
from zipfile import BadZipFile, ZipFile

from flightops.common.checksums import file_sha256
from flightops.ingestion.errors import IngestionError


@dataclass(frozen=True)
class SourceInput:
    path: Path
    container_type: str
    csv_member_name: str | None
    archive_sha256: str | None
    archive_size_bytes: int

    @contextmanager
    def open_csv_binary(self) -> Iterator[BinaryIO]:
        """Open decompressed CSV bytes while keeping any ZIP owner alive."""

        if self.container_type == "csv":
            with self.path.open("rb") as stream:
                yield stream
            return
        with ZipFile(self.path) as archive:
            assert self.csv_member_name is not None
            with archive.open(self.csv_member_name, "r") as stream:
                yield stream


def _safe_zip_member(name: str) -> bool:
    path = PurePosixPath(name)
    return not path.is_absolute() and ".." not in path.parts


def prepare_source(path: str | Path) -> SourceInput:
    """Validate one CSV/ZIP container and return a reusable stream source."""

    source_path = Path(path).expanduser().resolve()
    if not source_path.is_file():
        raise IngestionError("INPUT_NOT_FILE", str(source_path), stage="discovery")
    suffix = source_path.suffix.lower()
    if suffix == ".csv":
        return SourceInput(
            path=source_path,
            container_type="csv",
            csv_member_name=None,
            archive_sha256=None,
            archive_size_bytes=source_path.stat().st_size,
        )
    if suffix != ".zip":
        raise IngestionError(
            "UNSUPPORTED_INPUT", f"Expected .csv or .zip: {source_path}", stage="discovery"
        )
    try:
        archive_sha = file_sha256(source_path)
        with ZipFile(source_path) as archive:
            unsafe = [item.filename for item in archive.infolist() if not _safe_zip_member(item.filename)]
            if unsafe:
                raise IngestionError(
                    "UNSAFE_ZIP_MEMBER", f"Unsafe ZIP member: {unsafe[0]}", stage="archive"
                )
            corrupt = archive.testzip()
            if corrupt:
                raise IngestionError(
                    "CORRUPT_ZIP", f"CRC check failed for {corrupt}", stage="archive"
                )
            csv_members = [
                item.filename
                for item in archive.infolist()
                if not item.is_dir() and item.filename.lower().endswith(".csv")
            ]
    except BadZipFile as exc:
        raise IngestionError("CORRUPT_ZIP", str(source_path), stage="archive") from exc
    if len(csv_members) != 1:
        raise IngestionError(
            "CSV_MEMBER_COUNT",
            f"Expected exactly one CSV in {source_path.name}; found {len(csv_members)}",
            stage="archive",
        )
    return SourceInput(
        path=source_path,
        container_type="zip",
        csv_member_name=csv_members[0],
        archive_sha256=archive_sha,
        archive_size_bytes=source_path.stat().st_size,
    )


def discover_inputs(paths: list[str | Path]) -> list[Path]:
    """Find CSV and ZIP inputs recursively, in deterministic path order."""

    discovered: set[Path] = set()
    for raw_path in paths:
        path = Path(raw_path).expanduser().resolve()
        if path.is_file():
            if path.suffix.lower() not in {".csv", ".zip"}:
                raise IngestionError(
                    "UNSUPPORTED_INPUT", f"Expected .csv or .zip: {path}", stage="discovery"
                )
            discovered.add(path)
        elif path.is_dir():
            discovered.update(
                item.resolve()
                for item in path.rglob("*")
                if item.is_file() and item.suffix.lower() in {".csv", ".zip"}
            )
        else:
            raise IngestionError("INPUT_NOT_FOUND", str(path), stage="discovery")
    return sorted(discovered, key=lambda item: str(item))
