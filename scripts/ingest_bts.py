#!/usr/bin/env python3
"""Repository-local entry point for the BTS ingestion CLI."""

from flightops.ingestion.cli import main


if __name__ == "__main__":
    raise SystemExit(main())
