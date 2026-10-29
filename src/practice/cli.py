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
from practice.catalog_commands import run_catalog_command
from practice.catalog_refresh import DEFAULT_SOURCE
from practice.classification import CONTENT_CLASSES
from practice.clock import ClockError
from practice.curriculum import DEFAULT_CURRICULUM_PATH
from practice.curriculum_commands import run_curriculum_command
from practice.exit_codes import EXIT_BAD_INPUT, EXIT_NOT_PASSED, EXIT_USAGE
from practice.knowledge import run_knowledge_command
from practice.lists import DEFAULT_LISTS_DIR
from practice.lists_commands import run_lists_command
from practice.menu_commands import make_environment, run_menu_command
from practice.package import PackageError, load_package
from practice.paths import REFERENCES_DIR, REPO_ROOT, resolve_practice_dir
from practice.readiness_commands import run_readiness_command
from practice.recommend_commands import run_recommend_command
from practice.request_commands import run_request_command
from practice.review_commands import run_review_command
from practice.rubric import APPROACH_MAX, CORRECTNESS_MAX, SPACE_BONUS_MAX, TIME_MAX
from practice.runner import RunResult, run_exercise
from practice.search import search
from practice.source_commands import run_sources_command
from practice.sources import DEFAULT_ACTOR
from practice.tutor_commands import run_tutor_command
from practice.tutor_request import ACTIONS

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
    parser.add_argument(
        "--references",
        type=Path,
        default=REFERENCES_DIR,
        help="preserved reference sources and manifests (default: references/)",
    )
    parser.add_argument(
        "--problems-dir",
        type=Path,
        default=REPO_ROOT / "problems",
        help="where exercise packages live (default: problems/)",
    )
    parser.add_argument(
        "--curriculum",
        type=Path,
        default=DEFAULT_CURRICULUM_PATH,
        help="curriculum file for recommendations (default: curriculum/core.json)",
    )
    parser.add_argument(
        "--lists-dir",
        type=Path,
        default=DEFAULT_LISTS_DIR,
        help="curated problem lists (default: catalog/lists/)",
    )
    commands = parser.add_subparsers(dest="command", required=True)
    catalog = commands.add_parser("catalog", help="refresh catalog metadata")
    actions = catalog.add_subparsers(dest="catalog_command", required=True)
    refresh = actions.add_parser("refresh", help="validate and replace the snapshot")
    refresh.add_argument("--source", default=DEFAULT_SOURCE)
    refresh.add_argument("--json", action="store_true")
    find = commands.add_parser("search", help="find problems by ID, title or slug")
    find.add_argument(
        "query",
        nargs="+",
        help="a problem ID, a title fragment or a slug; several words need no quotes",
    )
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
    curriculum = commands.add_parser(
        "curriculum", help="check the map or list next objectives"
    )
    actions = curriculum.add_subparsers(dest="curriculum_command", required=True)
    for action in ("check", "next"):
        sub = actions.add_parser(action)
        sub.add_argument("--file", type=Path, default=DEFAULT_CURRICULUM_PATH)
        sub.add_argument("--json", action="store_true")
    lists = commands.add_parser(
        "lists", help="browse curated problem lists such as Blind 75"
    )
    lists.add_argument("--json", action="store_true", help="print the summary as JSON")
    list_actions = lists.add_subparsers(dest="lists_command")
    show = list_actions.add_parser("show", help="show one list with a status each")
    show.add_argument("list_id", help="a list id from `practice lists`")
    show.add_argument("--json", action="store_true", default=argparse.SUPPRESS)
    check = list_actions.add_parser("check", help="validate every list file")
    check.add_argument("--json", action="store_true", default=argparse.SUPPRESS)
    add_attempt_commands(commands)
    ready = commands.add_parser(
        "readiness", help="report whether a problem's package is ready to practice"
    )
    ready.add_argument("platform")
    ready.add_argument("problem_id")
    ready.add_argument(
        "--package", type=Path, default=None, help="package directory to check"
    )
    ready.add_argument("--json", action="store_true", help="print the report as JSON")
    add_sources_commands(commands)
    add_tutor_commands(commands)
    add_request_command(commands)
    add_review_commands(commands)
    add_recommend_command(commands)
    add_menu_commands(commands)
    knowledge = commands.add_parser(
        "knowledge", help="export selected public knowledge"
    )
    exports = knowledge.add_subparsers(dest="knowledge_command", required=True)
    export = exports.add_parser("export", help="write deterministic source-aware JSON")
    export.add_argument("platform")
    export.add_argument("problem_id")
    export.add_argument("--language", default="python")
    export.add_argument("--mode", choices=("practice", "study"), default="practice")
    reveal = export.add_mutually_exclusive_group()
    reveal.add_argument("--hint-level", type=int, default=None)
    reveal.add_argument("--reveal-solution", action="store_true")
    export.add_argument("--source", action="append", default=[], metavar="ID")
    export.add_argument("--output", type=Path, default=None)
    return parser


def add_recommend_command(
    commands: "argparse._SubParsersAction[argparse.ArgumentParser]",
) -> None:
    recommend = commands.add_parser(
        "recommend",
        help="suggest what to practice next, with a plain reason",
        description="Shows one recommended problem and a few alternatives, each "
        "with the reason it was picked. It starts nothing and writes nothing. "
        "Starting any other problem is always allowed.",
    )
    recommend.add_argument("--json", action="store_true", help="print JSON")
    recommend.add_argument(
        "--choose",
        type=int,
        default=None,
        metavar="N",
        help="show pick N in full (1 is the recommendation) and how to start it",
    )


def add_review_commands(
    commands: "argparse._SubParsersAction[argparse.ArgumentParser]",
) -> None:
    review = commands.add_parser(
        "review",
        help="spaced reviews: see what is due and redo problems from a blank file",
        description="Reviews are derived from the journal. Nothing runs in the "
        "background and nothing sends reminders; run `review list` to see what is due.",
    )
    actions = review.add_subparsers(dest="review_command", required=True)
    actions.add_parser("list", help="show due and upcoming reviews")

    def identify(sub: argparse.ArgumentParser) -> None:
        sub.add_argument("platform")
        sub.add_argument("problem_id")
        sub.add_argument("--language", choices=LANGUAGES, default="python")

    start = actions.add_parser("start", help="begin a blank review attempt")
    identify(start)
    start.add_argument(
        "--package",
        type=Path,
        default=None,
        help="exercise package directory (default: problems/<platform>-<id>)",
    )
    skip = actions.add_parser("skip", help="postpone a review without any penalty")
    identify(skip)
    move = actions.add_parser("reschedule", help="choose the next review date")
    identify(move)
    when = move.add_mutually_exclusive_group(required=True)
    when.add_argument("--on", default=None, metavar="YYYY-MM-DD", help="a date")
    when.add_argument("--in-days", type=int, default=None, help="days from today")


def add_menu_commands(
    commands: "argparse._SubParsersAction[argparse.ArgumentParser]",
) -> None:
    menu = commands.add_parser(
        "menu",
        help="show the numbered chat menu, or run one item with: menu choose N",
        description="Prints a menu of numbered items. `practice menu choose N` runs "
        "item N and prints the result and the next menu. The screen is spelled in "
        "flags, so each call stands alone. Put `choose N` before the flags.",
    )
    menu.add_argument(
        "steps", nargs="*", metavar="choose N", help="run item N of the menu"
    )
    menu.add_argument("--attempt", default=None, help="the menu for this attempt")
    menu.add_argument(
        "--problem",
        nargs=2,
        metavar=("PLATFORM", "ID"),
        default=None,
        help="the menu for one problem",
    )
    menu.add_argument(
        "--browse",
        nargs="*",
        metavar="WORD",
        default=None,
        help="list problems; words search the catalog, none lists packages",
    )
    menu.add_argument("--reviews", action="store_true", help="the menu of due reviews")
    menu.add_argument(
        "--recommend", action="store_true", help="the menu with the recommendation"
    )
    menu.add_argument(
        "--confirm-reveal",
        action="store_true",
        help="confirm an item that reveals the full solution",
    )
    commands.add_parser(
        "tui",
        help="interactive arrow-key menu (needs a terminal; else use: menu)",
    )


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

    explain = actions.add_parser(
        "explain",
        help="record an explanation assessment, separate from tests and optimization",
    )
    explain.add_argument("attempt_id")
    for flag, limit, text in (
        ("approach", APPROACH_MAX, "the approach"),
        ("correctness", CORRECTNESS_MAX, "why it works"),
        ("time", TIME_MAX, "time complexity"),
        ("space", SPACE_BONUS_MAX, "space complexity, a bonus outside the core 10"),
    ):
        explain.add_argument(
            f"--{flag}",
            type=int,
            default=None,
            help=f"{text}, 0 to {limit}; leave out if not assessed",
        )
    explain.add_argument(
        "--ungraded",
        action="store_true",
        help="record that no component was assessed (not the same as zero)",
    )
    explain.add_argument("--evidence", required=True, help="what the learner said")
    explain.add_argument("--feedback", required=True, help="brief feedback given")
    explain.add_argument(
        "--coaching",
        default=None,
        help="optional optimization coaching note; never scored",
    )

    finish = actions.add_parser("finish", help="close an attempt, keeping its history")
    finish.add_argument("attempt_id")

    progress = commands.add_parser("progress", help="show progress from the journal")
    progress.add_argument("platform", nargs="?")
    progress.add_argument("problem_id", nargs="?")
    notes = commands.add_parser("notes", help="show one attempt's recorded timeline")
    notes.add_argument("attempt_id")


def add_sources_commands(
    commands: "argparse._SubParsersAction[argparse.ArgumentParser]",
) -> None:
    sources = commands.add_parser(
        "sources", help="preserve and verify published reference sources"
    )
    actions = sources.add_subparsers(dest="sources_command", required=True)
    classes = sorted(CONTENT_CLASSES)

    add = actions.add_parser("add", help="fetch one upstream file and its notice")
    add.add_argument("source_id", help="lowercase id for the new entry")
    add.add_argument(
        "--repository", required=True, help="https://github.com/OWNER/REPO"
    )
    add.add_argument("--revision", required=True, help="the full 40 character commit")
    add.add_argument("--path", required=True, help="the file's path in the repository")
    add.add_argument("--license-path", required=True, help="the notice's path there")
    add.add_argument("--license-id", required=True, help="license identifier, e.g. MIT")
    add.add_argument("--terms", required=True, help="the license terms in a sentence")
    add.add_argument("--policy-note", default=None, help="needed if not permissive")
    add.add_argument("--language", default="python")
    add.add_argument("--classification", choices=classes, required=True)
    add.add_argument("--title", required=True)
    add.add_argument("--raw-base", default=None, help="raw download base URL override")
    add.add_argument("--actor", default=DEFAULT_ACTOR, help="who ran the fetch")

    local = actions.add_parser(
        "add-local", help="register an adaptation or an original implementation"
    )
    local.add_argument("source_id")
    local.add_argument("--kind", choices=("adaptation", "original"), required=True)
    local.add_argument("--file", type=Path, required=True, help="the code to keep")
    local.add_argument("--language", default="python")
    local.add_argument("--classification", choices=classes, required=True)
    local.add_argument("--title", required=True)
    local.add_argument("--actor", default=DEFAULT_ACTOR)
    local.add_argument("--derived-from", default=None, help="upstream id (adaptation)")
    local.add_argument("--transformation", default=None, help="what was changed")

    validate = actions.add_parser(
        "validate", help="run a preserved file against a package and record the result"
    )
    validate.add_argument("source_id")
    validate.add_argument("--package", type=Path, required=True)
    validate.add_argument("--timeout", type=float, default=10.0)
    actions.add_parser("verify", help="check every manifest, hash and notice")
    show = actions.add_parser("show", help="show the citation record for a source")
    show.add_argument("source_id")
    show.add_argument("--json", action="store_true", help="print the record as JSON")
    actions.add_parser("list", help="list imported source ids")


def add_tutor_commands(
    commands: "argparse._SubParsersAction[argparse.ArgumentParser]",
) -> None:
    tutor = commands.add_parser(
        "tutor", help="check the tutor contract and start practice sessions"
    )
    actions = tutor.add_subparsers(dest="tutor_command", required=True)
    check = actions.add_parser("check", help="verify the tutor policy and its scoping")
    check.add_argument(
        "--root",
        type=Path,
        default=None,
        help="repository to check (default: this one)",
    )
    actions.add_parser("start", help="print safe session settings for a tutor session")
    actions.add_parser("classes", help="print the content class list for the policy")


def add_request_command(
    commands: "argparse._SubParsersAction[argparse.ArgumentParser]",
) -> None:
    request = commands.add_parser(
        "request",
        help="prepare a paste-ready request for an existing tutor chat",
        description="Writes a spoiler-aware request under the practice directory "
        "and prints it. Nothing is sent, and no help is recorded as given.",
    )
    request.add_argument("attempt_id")
    request.add_argument(
        "--action", choices=sorted(ACTIONS), required=True, help="what to ask the tutor"
    )
    request.add_argument(
        "--mode", choices=MODES, default="practice", help="default: practice"
    )
    request.add_argument(
        "--timed",
        action="store_true",
        help="timed practice for this request only; never carried forward",
    )
    request.add_argument(
        "--reveal",
        default=None,
        help="a hint level such as 2 to choose that hint, or 'solution' (required "
        "by explain-solution) to authorize the full solution",
    )
    request.add_argument(
        "--package",
        type=Path,
        default=None,
        help="exercise package directory (default: problems/<platform>-<id>)",
    )


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
    try:
        return dispatch(argv)
    except ClockError as error:
        print(f"practice: error: {error}", file=sys.stderr)
        return EXIT_USAGE


def dispatch(argv: list[str]) -> int:
    args = build_parser().parse_args(argv)
    if args.command == "catalog":
        return run_catalog_command(args)
    if args.command == "knowledge":
        private = resolve_practice_dir(args.practice_dir, os.environ)
        return run_knowledge_command(args, private)
    if args.command == "curriculum":
        return run_curriculum_command(args)
    if args.command == "lists":
        return run_lists_command(args)
    if args.command == "run":
        return run_command(args)
    if args.command == "tutor":
        practice_dir = resolve_practice_dir(args.practice_dir, os.environ)
        return run_tutor_command(args, practice_dir, REPO_ROOT)
    if args.command == "request":
        practice_dir = resolve_practice_dir(args.practice_dir, os.environ)
        return run_request_command(args, practice_dir)
    if args.command in ("menu", "tui"):
        return run_menu_entry(args)
    if args.command == "readiness":
        return run_readiness_command(args, args.references)
    if args.command == "sources":
        return run_sources_command(args, args.references)
    if args.command == "recommend":
        practice_dir = resolve_practice_dir(args.practice_dir, os.environ)
        return run_recommend_command(args, practice_dir)
    if args.command == "review":
        practice_dir = resolve_practice_dir(args.practice_dir, os.environ)
        return run_review_command(args, practice_dir)
    if args.command in ("attempt", "progress", "notes"):
        practice_dir = resolve_practice_dir(args.practice_dir, os.environ)
        return run_attempt_command(args, practice_dir)
    try:
        catalog = load_catalog(args.catalog)
    except CatalogError as error:
        print(f"practice: error: {error}", file=sys.stderr)
        return EXIT_BAD_INPUT

    query = " ".join(args.query)
    matches = search(catalog, query)
    if not matches:
        print(f"No LeetCode problems match {query!r}.")
        return EXIT_NOT_PASSED
    for entry in matches[:MAX_RESULTS]:
        print(format_entry(entry))
    hidden = len(matches) - MAX_RESULTS
    if hidden > 0:
        print(f"... and {hidden} more. Refine your query to narrow the results.")
    return 0


def run_menu_entry(args: argparse.Namespace) -> int:
    practice_dir = resolve_practice_dir(args.practice_dir, os.environ)
    env = make_environment(
        practice_dir,
        args.catalog,
        args.problems_dir,
        args.references,
        main,
        args.curriculum,
    )
    if args.command == "menu":
        return run_menu_command(args, env)
    # Imported here so only an interactive session loads the terminal library.
    from practice.menu_tui import NOT_A_TERMINAL, run_tui, stdio_is_terminal

    if not stdio_is_terminal():
        print(NOT_A_TERMINAL, file=sys.stderr)
        return EXIT_USAGE
    return run_tui(env)


def run() -> None:
    # Titles contain non-ASCII characters; avoid the console's legacy encoding.
    if isinstance(sys.stdout, io.TextIOWrapper):
        sys.stdout.reconfigure(encoding="utf-8")
    sys.exit(main(sys.argv[1:]))
