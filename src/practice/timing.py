# ABOUTME: Timing evidence for opt-in timed attempts, derived from journal timestamps.
# ABOUTME: Evidence only: nothing here feeds scores, completion, reviews or advice.

from dataclasses import dataclass
from datetime import datetime, timedelta

from practice.history import Attempt

SEPARATE_NOTE = "separate from explanation feedback and test results"
NEVER_AFFECTS = (
    "Timing never changes explanation scores, completion, review rungs or "
    "recommendations."
)


class TimingError(Exception):
    """A timing choice is not valid, so nothing was started."""


@dataclass(frozen=True)
class TimingReport:
    timed: bool
    limit_minutes: int | None
    started_at: str
    first_pass: timedelta | None  # Start to the first passing local run.
    finished: timedelta | None  # Start to the finish event.
    open_elapsed: timedelta | None  # Start to now, only for an unfinished attempt.


def validate_limit(timed: bool, limit_minutes: int | None) -> None:
    """A limit belongs to a timed attempt and is a positive number of minutes."""
    if limit_minutes is None:
        return
    if not timed:
        raise TimingError("--limit-minutes needs --timed; timing is chosen explicitly")
    if limit_minutes <= 0:
        raise TimingError("--limit-minutes must be a positive number of minutes")


def timing_report(attempt: Attempt, now: datetime) -> TimingReport:
    """Elapsed times read from the attempt's journal timestamps and the given now."""
    if not attempt.timed:
        return TimingReport(False, None, attempt.started_at, None, None, None)
    started = _moment(attempt.started_at)
    first_pass = next(
        (
            e
            for e in attempt.events
            if e["type"] == "test_run" and e["status"] == "passed"
        ),
        None,
    )
    return TimingReport(
        timed=True,
        limit_minutes=attempt.limit_minutes,
        started_at=attempt.started_at,
        first_pass=_since(started, first_pass["at"]) if first_pass else None,
        finished=_since(started, attempt.finished_at) if attempt.finished_at else None,
        open_elapsed=None if attempt.finished_at else max(now - started, timedelta(0)),
    )


def format_timing(report: TimingReport) -> list[str]:
    """The timing section, labelled so it is never read as feedback or test results."""
    if not report.timed:
        return ["Untimed attempt: nothing was timed, and no speed is held against it."]
    lines = [
        f"Timing (evidence only, {SEPARATE_NOTE}):",
        f"  Timer started: {report.started_at}",
        f"  Limit: {_limit(report.limit_minutes)}",
        "  First passing run: " + _stop(report.first_pass, report, "none yet"),
    ]
    if report.finished is not None:
        lines.append("  Finished: " + _stop(report.finished, report, ""))
    elif report.open_elapsed is not None:
        lines.append(
            f"  Not finished: {format_duration(report.open_elapsed)} elapsed so far"
            + _remaining(report.open_elapsed, report.limit_minutes)
        )
    lines.append(f"  {NEVER_AFFECTS}")
    return lines


def format_duration(span: timedelta) -> str:
    seconds = int(span.total_seconds())
    hours, rest = divmod(seconds, 3600)
    minutes, secs = divmod(rest, 60)
    if hours:
        return f"{hours}h {minutes:02d}m {secs:02d}s"
    return f"{minutes}m {secs:02d}s"


def _limit(limit_minutes: int | None) -> str:
    if limit_minutes is None:
        return "none set"
    return f"{limit_minutes} minutes"


def _stop(span: timedelta | None, report: TimingReport, missing: str) -> str:
    if span is None:
        return missing
    return f"{format_duration(span)} after start{_against_limit(span, report)}"


def _against_limit(span: timedelta, report: TimingReport) -> str:
    if report.limit_minutes is None:
        return ""
    limit = timedelta(minutes=report.limit_minutes)
    if span <= limit:
        return f" (within the {report.limit_minutes} minute limit)"
    return (
        f" (over the {report.limit_minutes} minute limit by "
        f"{format_duration(span - limit)})"
    )


def _remaining(elapsed: timedelta, limit_minutes: int | None) -> str:
    if limit_minutes is None:
        return ""
    limit = timedelta(minutes=limit_minutes)
    if elapsed <= limit:
        return f" ({format_duration(limit - elapsed)} left of the limit)"
    return (
        f" (over the {limit_minutes} minute limit by "
        f"{format_duration(elapsed - limit)})"
    )


def _since(started: datetime, at: str) -> timedelta:
    return max(_moment(at) - started, timedelta(0))


def _moment(text: str) -> datetime:
    return datetime.fromisoformat(text)
