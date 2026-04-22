"""CLI: `python -m analyzer lint <file.sql>`"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from analyzer.parser import parse_script
from analyzer.linter import format_report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="analyzer", description="Analyze SQL SELECT queries.")
    sub = parser.add_subparsers(dest="cmd", required=True)

    lint_cmd = sub.add_parser("lint", help="Lint a SQL file.")
    lint_cmd.add_argument("file", help="Path to a .sql file with one or more SELECTs.")

    args = parser.parse_args(argv)

    if args.cmd == "lint":
        text = Path(args.file).read_text()
        queries = parse_script(text)
        for i, q in enumerate(queries, start=1):
            print(f"=== query {i} ===")
            print(format_report(q))
            print()
        return 0
    return 1


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
