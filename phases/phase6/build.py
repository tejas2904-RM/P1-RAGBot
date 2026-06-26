"""Phase 6 Render build — verify corpus artifacts before deploy."""

from __future__ import annotations

import sys

from phases import paths
from phases.phase6.bootstrap import apply_secrets, ensure_embedded_corpus


def main() -> int:
    """Validate that the deploy bundle can bootstrap the vector index on Render."""
    apply_secrets()

    if not paths.CHUNKS_FILE.exists() and not paths.EMBEDDED_CHUNKS_FILE.exists():
        print(
            "ERROR: corpus/processed/chunks.json and embedded_chunks.json are missing.",
            file=sys.stderr,
        )
        return 1

    try:
        ensure_embedded_corpus()
    except Exception as exc:
        print(f"ERROR: failed to prepare embedded corpus: {exc}", file=sys.stderr)
        return 1

    if not paths.EMBEDDED_CHUNKS_FILE.exists():
        print("ERROR: embedded_chunks.json was not created.", file=sys.stderr)
        return 1

    print(f"OK: embedded corpus ready at {paths.EMBEDDED_CHUNKS_FILE}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
