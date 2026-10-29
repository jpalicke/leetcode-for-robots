# ABOUTME: Command handlers for spaced reviews: list, start, skip and reschedule.
# ABOUTME: Reads the schedule from the journal and never prints earlier solution code.

import argparse
import sys
from datetime import date, timedelta
from pathlib import Path

from practice import clock
from practice.attempt_commands import describe_attempt
from practice.attempts import start_attempt
from practice.catalog import CatalogError, load_catalog
from practice.exit_codes import EXIT_BAD_INPUT, EXIT_USAGE
from practice.history import AttemptError, find_attempt, load_history
from practice.journal import JournalError
from practice.package import PackageError, load_package
from practice.paths import default_package_dir
from practice.reviews import (
    ReviewError,
    ReviewItem,
    ReviewSchedule,
    describe_review,
    load_schedule,
    record_reschedule,
    record_skip,
)

NONE_LINE = "  (none)"


def run_review_command(args: argparse.Namespace, practice_dir: Path) -> int:
    try:
        return _dispatch(args, practice_dir)
    except (AttemptError, ReviewError, clock.ClockError) as error:
        print(f"practice: error: {error}", file=sys.stderr)
        return EXIT_USAGE
    except (CatalogError, PackageError, JournalError) as error:
        print(f"practice: error: {error}", file=sys.stderr)
        return EXIT_BAD_INPUT


def _dispatch(args: argparse.Namespace, practice_dir: Path) -> int:
    handlers = {
        "list": _list,
        "start": _start,
        "skip": _skip,
        "reschedule": _reschedule,
    }
    return handlers[args.review_command](args, practice_dir)


def _schedule(practice_dir: Path) -> ReviewSchedule:
    schedule = load_schedule(practice_dir)
    for notice in schedule.notices:
        print(f"practice: warning: {notice}", file=sys.stderr)
    return schedule


def _list(args: argparse.Namespace, practice_dir: Path) -> int:
    today = clock.today()
    schedule = _schedule(practice_dir)
    if not schedule.items:
        print("No reviews scheduled.")
        print("A problem becomes review-eligible once an attempt of it passes locally.")
        return 0
    print(f"Reviews as of {today.isoformat()}")
    print("Due now:")
    _print_items(schedule.due(today))
    print("Upcoming:")
    _print_items(schedule.upcoming(today))
    return 0


def _print_items(items: list[ReviewItem]) -> None:
    if not items:
        print(NONE_LINE)
    for item in items:
        print(f"  {describe_review(item)}")
        if item.open_attempt_id:
            print(
                f"    review in progress: attempt {item.open_attempt_id}  "
                f"(continue with: practice attempt resume "
                f"{item.platform} {item.problem_id})"
            )


def _start(args: argparse.Namespace, practice_dir: Path) -> int:
    today = clock.today()
    item = _scheduled(practice_dir, args.platform, args.problem_id, args.language)
    if item.open_attempt_id:
        raise ReviewError(
            f"review attempt {item.open_attempt_id} is already open; continue it with: "
            f"practice attempt resume {args.platform} {args.problem_id}"
        )
    catalog = load_catalog(args.catalog)
    package = load_package(
        args.package or default_package_dir(args.platform, args.problem_id)
    )
    started = start_attempt(
        practice_dir,
        catalog,
        package,
        args.platform,
        args.problem_id,
        language=args.language,
        mode="practice",
        timed=False,
        review=True,
    )
    attempt = find_attempt(load_history(practice_dir), started.attempt_id)
    print(f"Started review attempt {started.attempt_id}")
    print(describe_attempt(attempt))
    print(f"Code: {started.code_path}")
    print(f"Starter: {started.starter_source}")
    if not item.is_due(today):
        print(f"Note: this review is not due until {item.due_on.isoformat()}.")
    print(
        "Earlier solutions are kept on disk and are not shown. Start from the starter."
    )
    return 0


def _skip(args: argparse.Namespace, practice_dir: Path) -> int:
    item = _scheduled(practice_dir, args.platform, args.problem_id, args.language)
    record_skip(practice_dir, item)
    moved = _scheduled(practice_dir, args.platform, args.problem_id, args.language)
    print(f"Skipped the review of {args.platform} {args.problem_id} ({args.language}).")
    print(f"Next review: {moved.due_on.isoformat()}. No score is affected.")
    return 0


def _reschedule(args: argparse.Namespace, practice_dir: Path) -> int:
    today = clock.today()
    if args.on is not None:
        try:
            due_on = date.fromisoformat(args.on)
        except ValueError:
            raise ReviewError(
                f"--on needs a date like 2026-12-25, not {args.on!r}"
            ) from None
    else:
        if args.in_days < 0:
            raise ReviewError("--in-days must be zero or more")
        due_on = today + timedelta(days=args.in_days)
    if due_on < today:
        raise ReviewError(f"{due_on.isoformat()} is in the past; pick today or later")
    item = _scheduled(practice_dir, args.platform, args.problem_id, args.language)
    record_reschedule(practice_dir, item, due_on)
    print(
        f"Rescheduled the review of {args.platform} {args.problem_id} "
        f"({args.language}) to {due_on.isoformat()}. No score is affected."
    )
    return 0


def _scheduled(
    practice_dir: Path, platform: str, problem_id: str, language: str
) -> ReviewItem:
    item = _schedule(practice_dir).find(platform, problem_id, language)
    if item is None:
        raise ReviewError(
            f"no review is scheduled for {platform} {problem_id} ({language}); "
            "pass the problem locally first"
        )
    return item
