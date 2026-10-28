# ABOUTME: Command line entry point for the practice tool.
# ABOUTME: Exit codes: 0 success, 1 no match or not passed, 2 usage, 3 invalid input.

import argparse
import io
import json
import math
import os
import sys
from pathlib import Path

from practice.attempt_commands import run_attempt_command
from practice.attempts import (
    ASSISTANCE_KINDS,
    LANGUAGES,
    MODES,
    VERDICT_STATUSES,
)
from practice.catalog import DEFAULT_CATALOG_PATH, CatalogError, Entry, load_catalog
from practice.exit_codes import EXIT_BAD_INPUT, EXIT_NOT_PASSED, EXIT_USAGE
from practice.package import PackageError, load_package
from practice.paths import resolve_practice_dir
from practice.runner import RunResult, run_exercise
from practice.search import search

MAX_RESULTS = 20
DEFAULT_TIMEOUT_SECONDS = 10.0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="practice")
    parser.add_argument(
        "--catalog",
        type=Path,
        default=DEFAULT_CATALOG_PATH,
        help="catalog file to use (default: the committed LeetCode snapshot)",
    )
    parser.add_argument(
        "--practice-dir",
        type=Path,
        default=None,
        help="where private attempts and the journal live "
        "(default: $PRACTICE_DIR, else .practice/ in the repository)",
    )
    commands = parser.add_subparsers(dest="command", required=True)
    find = commands.add_parser("search", help="find problems by ID, title or slug")
    find.add_argument("query", help="a problem ID, a title fragment or a slug")
    run = commands.add_parser("run", help="run a solution against an exercise package")
    run.add_argument("package", type=Path, help="the exercise package directory")
    run.add_argument("solution", type=Path, help="the Python file with the solution")
    run.add_argument(
        "--timeout",
        type=float,
        default=DEFAULT_TIMEOUT_SECONDS,
        help=f"seconds for the whole run (default: {DEFAULT_TIMEOUT_SECONDS:g})",
    )
    run.add_argument(
        "--json", action="store_true", help="print the full result as JSON"
    )
    add_attempt_commands(commands)
    return parser


def add_attempt_commands(
    commands: "argparse._SubParsersAction[argparse.ArgumentParser]",
) -> None:
    package_help = "exercise package directory (default: problems/<platform>-<id>)"
    attempt = commands.add_parser("attempt", help="start, resume and record attempts")
    actions = attempt.add_subparsers(dest="attempt_command", required=True)

    start = actions.add_parser("start", help="begin a new blank attempt")
    start.add_argument("platform")
    start.add_argument("problem_id")
    start.add_argument("--language", choices=LANGUAGES, default="python")
    start.add_argument("--mode", choices=MODES, default="practice")
    start.add_argument("--timed", action="store_true", help="mark this attempt timed")
    start.add_argument("--package", type=Path, default=None, help=package_help)

    for name, text in (
        ("resume", "show the latest unfinished attempt"),
        ("list", "list attempts"),
    ):
        sub = actions.add_parser(name, help=text)
        sub.add_argument("platform", nargs="?")
        sub.add_argument("problem_id", nargs="?")

    test = actions.add_parser("test", help="run an attempt and record the result")
    test.add_argument("attempt_id")
    test.add_argument("--package", type=Path, default=None, help=package_help)
    test.add_argument("--timeout", type=float, default=DEFAULT_TIMEOUT_SECONDS)

    assist = actions.add_parser(
        "note-assistance", help="record help that was actually delivered"
    )
    assist.add_argument("attempt_id")
    assist.add_argument("--kind", choices=ASSISTANCE_KINDS, required=True)
    assist.add_argument("--level", type=int, default=None, help="hint level, 0 to 3")
    assist.add_argument("--summary", default=None)

    verdict = actions.add_parser("verdict", help="record what the platform said")
    verdict.add_argument("attempt_id")
    verdict.add_argument("--status", choices=VERDICT_STATUSES, required=True)
    verdict.add_argument("--source", required=True, help="where you saw the verdict")
    verdict.add_argument("--date", default=None, help="ISO date (default: today, UTC)")

    finish = actions.add_parser("finish", help="close an attempt, keeping its history")
    finish.add_argument("attempt_id")

    progress = commands.add_parser("progress", help="show progress from the journal")
    progress.add_argument("platform", nargs="?")
    progress.add_argument("problem_id", nargs="?")
    notes = commands.add_parser("notes", help="show one attempt's recorded timeline")
    notes.add_argument("attempt_id")


def format_entry(entry: Entry) -> str:
    premium = " premium" if entry.paid_only else ""
    return (
        f"{entry.frontend_question_id:>5}  {entry.title}  "
        f"[{entry.difficulty}{premium}]  {entry.slug}"
    )


def format_run(result: RunResult) -> str:
    name = f"{result.platform}/{result.problem_id}"
    lines = [f"{result.status.upper()}  {name}: {result.message}"]
    for case in result.cases:
        if case.outcome in ("passed", "not_run"):
            continue
        lines.append(f"  {case.case_id}  {case.outcome}: {case.detail}")
        if case.actual is not None:
            lines.append(f"    actual:   {json.dumps(case.actual)}")
        if case.expected is not None:
            lines.append(f"    expected: {json.dumps(case.expected)}")
    lines.append(f"code sha256:   {result.code_sha256}")
    lines.append(f"suite sha256:  {result.suite_sha256 or 'none'}")
    lines.append(f"suite version: {result.suite_version or 'none'}")
    lines.append(f"run at:        {result.run_at} ({result.duration_seconds}s)")
    lines.extend(f"note: {note}" for note in result.notes)
    return "\n".join(lines)


def run_command(args: argparse.Namespace) -> int:
    if not (math.isfinite(args.timeout) and args.timeout > 0):
        build_parser().error("--timeout must be a number of seconds above zero")
    try:
        package = load_package(args.package)
    except PackageError as error:
        print(f"practice: error: {error}", file=sys.stderr)
        return EXIT_BAD_INPUT
    try:
        result = run_exercise(package, args.solution, timeout=args.timeout)
    except OSError as error:
        message = f"cannot read solution {args.solution}: {error}"
        print(f"practice: error: {message}", file=sys.stderr)
        return EXIT_USAGE
    if args.json:
        print(json.dumps(result.to_dict(), indent=2))
    else:
        print(format_run(result))
    return 0 if result.status == "passed" else EXIT_NOT_PASSED


def main(argv: list[str]) -> int:
    args = build_parser().parse_args(argv)
    if args.command == "run":
        return run_command(args)
    if args.command in ("attempt", "progress", "notes"):
        practice_dir = resolve_practice_dir(args.practice_dir, os.environ)
        return run_attempt_command(args, practice_dir)
    try:
        catalog = load_catalog(args.catalog)
    except CatalogError as error:
        print(f"practice: error: {error}", file=sys.stderr)
        return EXIT_BAD_INPUT

    matches = search(catalog, args.query)
    if not matches:
        print(f"No LeetCode problems match {args.query!r}.")
        return EXIT_NOT_PASSED
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
