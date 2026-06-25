"""Phase 3 CLI — ask factual questions against the indexed corpus."""

from __future__ import annotations

import argparse
import json
import sys

from phases.phase3.pipeline import answer_query


def main() -> None:
    parser = argparse.ArgumentParser(description="Phase 3 — RAG factual Q&A")
    parser.add_argument("query", nargs="?", help="User question")
    parser.add_argument("--json", action="store_true", help="Print RAGResponse as JSON")
    args = parser.parse_args()

    if not args.query:
        parser.error("query is required")

    response = answer_query(args.query)
    if args.json:
        print(json.dumps(response.to_dict(), indent=2))
    else:
        print(response.answer)

    raise SystemExit(0 if response.success else 1)


if __name__ == "__main__":
    main()
