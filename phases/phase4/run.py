"""Phase 4 CLI — classified assistant with refusal handling."""

from __future__ import annotations

import argparse
import json
import sys

from phases.phase4.pipeline import handle_query


def main() -> None:
    parser = argparse.ArgumentParser(description="Phase 4 — Classified FAQ assistant")
    parser.add_argument("query", nargs="?", help="User question")
    parser.add_argument("--json", action="store_true", help="Print AssistantResponse as JSON")
    args = parser.parse_args()

    if not args.query:
        parser.error("query is required")

    response = handle_query(args.query)
    if args.json:
        print(json.dumps(response.to_dict(), indent=2))
    else:
        print(response.answer)

    if response.refused:
        raise SystemExit(0)
    raise SystemExit(0 if response.success else 1)


if __name__ == "__main__":
    main()
