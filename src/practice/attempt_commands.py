# ABOUTME: Command handlers for attempts, progress and notes, all read from the journal.
# ABOUTME: Derived text is built fresh on every call and never includes solution code.

import argparse
import sys
from pathlib import Path

from practice.attempts import (
    finish_attempt,
    record_assistance,
    record_explanation,
    record_verdict,
    run_attempt_tests,
    start_attempt,
)
from practice.catalog import CatalogError, load_catalog
from practice.exit_codes import EXIT_BAD_INPUT, EXIT_NOT_PASSED, EXIT_USAGE
from practice.history import (
    STATUS_LABELS,
    Attempt,
    AttemptError,
    AttemptView,
    ExplanationView,
    History,
    find_attempt,
    latest_unfinished,
    load_history,
    summarize_problems,
    view_attempt,
)
from practice.journal import JournalError
from practice.package import ExercisePackage, PackageError, load_package
from practice.paths import default_package_dir
from practice.rubric import ExplanationScores, format_scores
from practice.runner import RunResult

HASH_PREFIX = 12


def run_attempt_command(args: argparse.Namespace, practice_dir: Path) -> int:
    try:
        return _dispatch(args, practice_dir)
    except AttemptError as error:
        print(f"practice: error: {error}", file=sys.stderr)
        return EXIT_USAGE
    except (CatalogError, PackageError, JournalError) as error:
        print(f"practice: error: {error}", file=sys.stderr)
        return EXIT_BAD_INPUT


def _dispatch(args: argparse.Namespace, practice_dir: Path) -> int:
    if args.command == "progress":
        return _progress(args, practice_dir)
    if args.command == "notes":
        return _notes(args, practice_dir)
    handlers = {
        "start": _start,
        "resume": _resume,
        "list": _list,
        "test": _test,
        "note-assistance": _note_assistance,
        "verdict": _verdict,
        "explain": _explain,
        "finish": _finish,
    }
    return handlers[args.attempt_command](args, practice_dir)


def _start(args: argparse.Namespace, practice_dir: Path) -> int:
    catalog = load_catalog(args.catalog)
    package = _load_package(args.package, args.platform, args.problem_id)
    started = start_attempt(
        practice_dir,
        catalog,
        package,
        args.platform,
        args.problem_id,
        language=args.language,
        mode=args.mode,
        timed=args.timed,
    )
    title = next(
        e.title
        for e in catalog.entries
        if str(e.frontend_question_id) == args.problem_id
    )
    print(f"Started attempt {started.attempt_id}")
    print(
        f"{args.platform} {args.problem_id}  {title}  "
        f"({args.language}, {args.mode}, {_timing(args.timed)})"
    )
    print(f"Code: {started.code_path}")
    print(f"Starter: {started.starter_source}")
    return 0


def _resume(args: argparse.Namespace, practice_dir: Path) -> int:
    if (args.platform is None) != (args.problem_id is None):
        return _usage("give both PLATFORM and PROBLEM_ID, or neither")
    history = _load(practice_dir)
    attempt = latest_unfinished(history, args.platform, args.problem_id)
    if attempt is None:
        print("No unfinished attempt to resume. Start one with: practice attempt start")
        return EXIT_NOT_PASSED
    view = view_attempt(attempt, practice_dir)
    print(f"Resume attempt {attempt.attempt_id}")
    print(describe_attempt(attempt))
    print(f"Status: {STATUS_LABELS[view.status]}")
    print(f"Code: {view.code_path}")
    if not view.code_path.is_file():
        print("Warning: the attempt file is missing or unreadable.")
    if view.latest_run is not None:
        print(f"Last test run: {view.latest_run['status']} at {view.latest_run['at']}")
    return 0


def _list(args: argparse.Namespace, practice_dir: Path) -> int:
    if (args.platform is None) != (args.problem_id is None):
        return _usage("give both PLATFORM and PROBLEM_ID, or neither")
    history = _load(practice_dir)
    shown = [
        a
        for a in history.attempts
        if args.platform is None
        or (a.platform, a.problem_id) == (args.platform, args.problem_id)
    ]
    if not shown:
        print("No attempts recorded.")
        return 0
    for attempt in shown:
        print(_attempt_line(view_attempt(attempt, practice_dir)))
    return 0


def _test(args: argparse.Namespace, practice_dir: Path) -> int:
    history = _load(practice_dir)
    attempt = find_attempt(history, args.attempt_id)
    package = _load_package(args.package, attempt.platform, attempt.problem_id)
    result = run_attempt_tests(practice_dir, attempt, package, args.timeout)
    print(format_result(result))
    print("Recorded this test run in the journal.")
    return 0 if result.status == "passed" else EXIT_NOT_PASSED


def _note_assistance(args: argparse.Namespace, practice_dir: Path) -> int:
    attempt = find_attempt(_load(practice_dir), args.attempt_id)
    record_assistance(practice_dir, attempt, args.kind, args.level, args.summary)
    print(f"Recorded {args.kind} assistance for attempt {attempt.attempt_id}.")
    return 0


def _verdict(args: argparse.Namespace, practice_dir: Path) -> int:
    attempt = find_attempt(_load(practice_dir), args.attempt_id)
    record_verdict(practice_dir, attempt, args.status, args.source, args.date)
    print(
        f"Recorded platform verdict {args.status} for attempt {attempt.attempt_id}. "
        "Local test results are unchanged."
    )
    return 0


def _explain(args: argparse.Namespace, practice_dir: Path) -> int:
    components = (args.approach, args.correctness, args.time, args.space)
    if args.ungraded and any(value is not None for value in components):
        return _usage("--ungraded cannot be combined with scores")
    if not args.ungraded and all(value is None for value in components):
        return _usage("give at least one score, or --ungraded if nothing was assessed")
    attempt = find_attempt(_load(practice_dir), args.attempt_id)
    scores = ExplanationScores(*components)
    record_explanation(
        practice_dir, attempt, scores, args.evidence, args.feedback, args.coaching
    )
    recorded = view_attempt(_reload(practice_dir, attempt), practice_dir)
    latest = recorded.latest_explanation
    assert latest is not None
    print(
        f"Recorded {latest.label} explanation assessment for attempt "
        f"{attempt.attempt_id}: {format_scores(scores)}."
    )
    if not latest.code_passed:
        print(
            "Note: no passing local run for this code, so this explanation is "
            "labelled as such."
        )
    print("Completion and local test results are unchanged.")
    return 0


def _finish(args: argparse.Namespace, practice_dir: Path) -> int:
    attempt = find_attempt(_load(practice_dir), args.attempt_id)
    finish_attempt(practice_dir, attempt)
    print(f"Finished attempt {attempt.attempt_id}. Its code and history are kept.")
    return 0


def _progress(args: argparse.Namespace, practice_dir: Path) -> int:
    if (args.platform is None) != (args.problem_id is None):
        return _usage("give both PLATFORM and PROBLEM_ID, or neither")
    history = _load(practice_dir)
    views = [view_attempt(a, practice_dir) for a in history.attempts]
    summaries = summarize_problems(views)
    if args.platform is not None:
        summaries = [
            s
            for s in summaries
            if (s.platform, s.problem_id) == (args.platform, args.problem_id)
        ]
        if not summaries:
            print(f"{args.platform} {args.problem_id}: not started")
            return 0
    if not summaries:
        print("No attempts yet. Start one with: practice attempt start")
        return 0
    for summary in summaries:
        print(
            f"{summary.platform} {summary.problem_id}  {summary.title}: "
            f"{STATUS_LABELS[summary.status]}"
        )
        print(f"  platform verdict: {_verdict_text(summary.verdict)}")
        for view in summary.attempts:
            print(f"  {_attempt_line(view)}")
            print(f"    explanation: {_explanation_summary(view.latest_explanation)}")
    return 0


def _notes(args: argparse.Namespace, practice_dir: Path) -> int:
    attempt = find_attempt(_load(practice_dir), args.attempt_id)
    view = view_attempt(attempt, practice_dir)
    print(f"Attempt {attempt.attempt_id}")
    print(describe_attempt(attempt))
    print(f"Status: {STATUS_LABELS[view.status]}")
    print("Timeline:")
    for event in attempt.events:
        text = _event_text(event)
        if text is not None:
            print(f"  {event['at']}  {text}")
    print("Explanation assessments (separate from tests and the platform verdict):")
    if not view.explanations:
        print("  No explanation assessed yet.")
    for explanation in view.explanations:
        _print_explanation(explanation)
    current = view.current_sha256
    print(f"Code now: {current[:HASH_PREFIX] if current else 'missing or unreadable'}")
    if view.latest_pass is not None:
        print(f"Last passing code: {view.latest_pass['code_sha256'][:HASH_PREFIX]}")
    print("Derived from the journal each time; edit nothing here.")
    return 0


def _print_explanation(explanation: ExplanationView) -> None:
    code = explanation.code_sha256
    print(
        f"  {explanation.sequence}. {explanation.label}  "
        f"{format_scores(explanation.scores)}  "
        f"{_currency(explanation)}  code {code[:HASH_PREFIX] if code else 'none'}"
    )
    if not explanation.code_passed:
        print("     no passing local run for this code")
    print(f"     evidence: {explanation.evidence}")
    print(f"     feedback: {explanation.feedback}")
    if explanation.coaching:
        print(f"     optimization coaching (not scored): {explanation.coaching}")


def _explanation_summary(explanation: ExplanationView | None) -> str:
    if explanation is None or explanation.scores.is_ungraded:
        return "not assessed"
    unproven = "" if explanation.code_passed else ", no passing local run"
    return (
        f"{format_scores(explanation.scores)} "
        f"({explanation.label}, {_currency(explanation)}{unproven})"
    )


def _currency(explanation: ExplanationView) -> str:
    return "current" if explanation.is_current else "stale after edit"


def format_result(result: RunResult) -> str:
    # Same layout as `practice run`, so the two commands read alike.
    from practice.cli import format_run

    return format_run(result)


def _event_text(event: dict[str, object]) -> str | None:
    kind = event["type"]
    if kind == "attempt_started":
        return (
            f"started ({event['language']}, {event['mode']}, "
            f"{_timing(bool(event['timed']))}; starter: {event.get('starter_source')})"
        )
    if kind == "test_run":
        headline = str(event["message"]).splitlines()[0]
        suite = str(event["suite_sha256"] or "none")[:HASH_PREFIX]
        return (
            f"test run: {event['status']} ({headline}); "
            f"code {str(event['code_sha256'])[:HASH_PREFIX]}, "
            f"suite {event['suite_version']} {suite}"
        )
    if kind == "assistance":
        level = f" level {event['level']}" if event.get("level") is not None else ""
        summary = f": {event['summary']}" if event.get("summary") else ""
        return f"assistance: {event['kind']}{level}{summary}"
    if kind == "platform_verdict":
        return (
            f"platform verdict: {event['status']} ({event['date']}, {event['source']})"
        )
    if kind == "explanation_assessment":
        return (
            f"explanation assessment: "
            f"{format_scores(ExplanationScores.from_record(event))}"
        )
    if kind == "attempt_finished":
        return "finished"
    return None  # Event types from newer versions are left out, not guessed at.


def _verdict_text(verdict: dict[str, object] | None) -> str:
    if verdict is None:
        return "none recorded"
    return f"{verdict['status']} ({verdict['date']}, {verdict['source']})"


def describe_attempt(attempt: Attempt) -> str:
    review = ", review" if attempt.review else ""
    return (
        f"{attempt.platform} {attempt.problem_id}  {attempt.title}  "
        f"({attempt.language}, {attempt.mode}, {_timing(attempt.timed)}{review})"
    )


def _attempt_line(view: AttemptView) -> str:
    attempt = view.attempt
    finished = "  finished" if attempt.finished_at else ""
    return (
        f"{attempt.attempt_id}  {attempt.platform} {attempt.problem_id}  "
        f"{attempt.language}  {attempt.mode}  {_timing(attempt.timed)}  "
        f"{STATUS_LABELS[view.status]}{finished}"
    )


def _timing(timed: bool) -> str:
    return "timed" if timed else "untimed"


def _load(practice_dir: Path) -> History:
    history = load_history(practice_dir)
    for notice in history.notices:
        print(f"practice: warning: {notice}", file=sys.stderr)
    return history


def _reload(practice_dir: Path, attempt: Attempt) -> Attempt:
    return find_attempt(load_history(practice_dir), attempt.attempt_id)


def _load_package(
    given: Path | None, platform: str, problem_id: str
) -> ExercisePackage:
    return load_package(given or default_package_dir(platform, problem_id))


def _usage(message: str) -> int:
    print(f"practice: error: {message}", file=sys.stderr)
    return EXIT_USAGE
