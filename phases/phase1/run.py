"""Phase 1 entry point — validate corpus config and fetch pinned Groww pages."""

from __future__ import annotations

import argparse
import sys

from phases import paths
from phases.phase1.fetcher import CorpusFetcher
from phases.phase1.registry import load_urls_config, save_scheme_registry, save_source_registry
from phases.phase1.validator import ValidationError, validate_urls_config


def run(*, fetch: bool = True, skip_fetch_on_error: bool = False) -> int:
    """Execute Phase 1 pipeline. Returns process exit code."""
    paths.CORPUS_DIR.mkdir(parents=True, exist_ok=True)
    paths.METADATA_DIR.mkdir(parents=True, exist_ok=True)
    paths.RAW_DIR.mkdir(parents=True, exist_ok=True)

    config = load_urls_config()
    validate_urls_config(config)

    registry_path = save_scheme_registry(config)
    print(f"Wrote scheme registry: {registry_path}")

    if not fetch:
        print("Skipping fetch (--no-fetch).")
        return 0

    with CorpusFetcher() as fetcher:
        records = fetcher.fetch_all(config.schemes)

    source_path = save_source_registry(records)
    print(f"Wrote source registry: {source_path}")

    failed = [record for record in records if record.status != "ok"]
    for record in records:
        status = record.status
        detail = record.raw_snapshot or record.error or "no detail"
        print(f"  [{status}] {record.scheme_id}: {detail}")

    if failed and not skip_fetch_on_error:
        print(f"\nPhase 1 fetch completed with {len(failed)} failure(s).", file=sys.stderr)
        return 1

    print("\nPhase 1 completed successfully.")
    return 0


def main() -> None:
    parser = argparse.ArgumentParser(description="Phase 1 — Corpus definition and source curation")
    parser.add_argument(
        "--no-fetch",
        action="store_true",
        help="Validate urls.json and write scheme_registry.json without fetching Groww pages",
    )
    parser.add_argument(
        "--skip-fetch-on-error",
        action="store_true",
        help="Return exit code 0 even if one or more fetches fail (for CI with partial availability)",
    )
    args = parser.parse_args()

    try:
        exit_code = run(fetch=not args.no_fetch, skip_fetch_on_error=args.skip_fetch_on_error)
    except ValidationError as exc:
        print(f"Validation error: {exc}", file=sys.stderr)
        exit_code = 1

    raise SystemExit(exit_code)


if __name__ == "__main__":
  main()
