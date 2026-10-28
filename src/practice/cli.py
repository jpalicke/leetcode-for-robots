# ABOUTME: Command line entry point for the practice tool.
# ABOUTME: Exit codes: 0 success, 1 no match, 2 usage error, 3 invalid catalog.

import argparse
import io
import sys
from pathlib import Path

from practice.catalog import DEFAULT_CATALOG_PATH, CatalogError, Entry, load_catalog
from practice.search import search

MAX_RESULTS = 20
EXIT_NO_MATCH = 1
EXIT_BAD_CATALOG = 3


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="practice")
    parser.add_argument(
        "--catalog",
        type=Path,
        default=DEFAULT_CATALOG_PATH,
        help="catalog file to use (default: the committed LeetCode snapshot)",
    )
    commands = parser.add_subparsers(dest="command", required=True)
    find = commands.add_parser("search", help="find problems by ID, title or slug")
    find.add_argument("query", help="a problem ID, a title fragment or a slug")
    return parser


def format_entry(entry: Entry) -> str:
    premium = " premium" if entry.paid_only else ""
    return (
        f"{entry.frontend_question_id:>5}  {entry.title}  "
        f"[{entry.difficulty}{premium}]  {entry.slug}"
    )


def main(argv: list[str]) -> int:
    args = build_parser().parse_args(argv)
    try:
        catalog = load_catalog(args.catalog)
    except CatalogError as error:
        print(f"practice: error: {error}", file=sys.stderr)
        return EXIT_BAD_CATALOG

    matches = search(catalog, args.query)
    if not matches:
        print(f"No LeetCode problems match {args.query!r}.")
        return EXIT_NO_MATCH
    for entry in matches[:MAX_RESULTS]:
        print(format_entry(entry))
    hidden = len(matches) - MAX_RESULTS
    if hidden > 0:
        print(f"... and {hidden} more. Refine your query to narrow the results.")
    return 0


def run() -> None:
    # Titles contain non-ASCII characters; avoid the console's legacy encoding.
    if isinstance(sys.stdout, io.TextIOWrapper):
        sys.stdout.reconfigure(encoding="utf-8")
    sys.exit(main(sys.argv[1:]))
