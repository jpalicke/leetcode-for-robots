# ABOUTME: Unit tests for timing evidence derived from journal timestamps and the limit.
# ABOUTME: Pure functions over real Attempt records; no clock or background process.

from datetime import UTC, datetime, timedelta

import pytest

from practice.history import Attempt, build_history
from practice.timing import (
    TimingError,
    format_duration,
    format_timing,
    timing_report,
    validate_limit,
)

START = "2026-11-02T09:00:00.000+00:00"


def stamp(minutes: float) -> str:
    moment = datetime(2026, 11, 2, 9, 0, tzinfo=UTC) + timedelta(minutes=minutes)
    return moment.isoformat(timespec="milliseconds")


def record(kind: str, at: str, **fields: object) -> dict[str, object]:
    return {
        "schema_version": 1,
        "event_id": f"{kind}-{at}",
        "at": at,
        "type": kind,
        "attempt_id": "A1",
        **fields,
    }


def started_record(*, timed: bool = True, limit: object = None) -> dict[str, object]:
    started: dict[str, object] = record(
        "attempt_started",
        START,
        platform="leetcode",
        problem_id="1",
        title="Two Sum",
        language="python",
        mode="practice",
        timed=timed,
    )
    if limit is not None:
        started["limit_minutes"] = limit
    return started


def attempt(
    *events: dict[str, object], timed: bool = True, limit: int | None = None
) -> Attempt:
    found = build_history([started_record(timed=timed, limit=limit), *events]).attempts
    assert len(found) == 1
    return found[0]


def now(minutes: float) -> datetime:
    return datetime.fromisoformat(stamp(minutes))


def text_of(found: Attempt, minutes: float) -> str:
    return "\n".join(format_timing(timing_report(found, now(minutes))))


def test_durations_read_as_minutes_and_seconds() -> None:
    assert format_duration(timedelta(seconds=0)) == "0m 00s"
    assert format_duration(timedelta(seconds=65)) == "1m 05s"
    assert format_duration(timedelta(minutes=125, seconds=9)) == "2h 05m 09s"


def test_an_untimed_attempt_records_no_timing() -> None:
    report = timing_report(attempt(timed=False), now(30))

    assert not report.timed
    assert report.first_pass is None and report.finished is None
    assert report.open_elapsed is None
    assert format_timing(report)[0].startswith("Untimed")


def test_elapsed_at_first_pass_and_finish_come_from_journal_timestamps() -> None:
    found = attempt(
        record("test_run", stamp(5), status="failed", code_sha256="a"),
        record("test_run", stamp(12.5), status="passed", code_sha256="b"),
        record("test_run", stamp(14), status="passed", code_sha256="b"),
        record("attempt_finished", stamp(20)),
        limit=45,
    )

    report = timing_report(found, now(999))

    assert report.first_pass == timedelta(minutes=12, seconds=30)
    assert report.finished == timedelta(minutes=20)
    assert report.open_elapsed is None  # Finished: nothing ticks any more.
    assert report.limit_minutes == 45


def test_the_report_says_within_or_over_the_limit() -> None:
    inside = attempt(
        record("test_run", stamp(30), status="passed", code_sha256="b"),
        record("attempt_finished", stamp(45)),
        limit=45,
    )
    over = attempt(
        record("test_run", stamp(50), status="passed", code_sha256="b"),
        record("attempt_finished", stamp(61)),
        limit=45,
    )

    inside_text = text_of(inside, 0)
    over_text = text_of(over, 0)

    assert "First passing run: 30m 00s after start (within the 45 minute limit)" in (
        inside_text
    )
    assert "Finished: 45m 00s after start (within the 45 minute limit)" in inside_text
    assert "First passing run: 50m 00s after start (over the 45 minute limit" in (
        over_text
    )
    assert "by 5m 00s)" in over_text
    assert "Finished: 1h 01m 00s after start (over the 45 minute limit by 16m 00s)" in (
        over_text
    )


def test_an_open_attempt_reports_elapsed_so_far_and_time_left() -> None:
    text = text_of(attempt(limit=45), 10)

    assert "Not finished: 10m 00s elapsed so far (35m 00s left of the limit)" in text
    assert "First passing run: none yet" in text


def test_an_open_attempt_past_its_limit_says_how_far() -> None:
    text = text_of(attempt(limit=45), 50)

    assert "over the 45 minute limit by 5m 00s" in text


def test_no_limit_means_no_within_or_over_claim() -> None:
    found = attempt(
        record("test_run", stamp(3), status="passed", code_sha256="b"),
        record("attempt_finished", stamp(4)),
    )

    text = text_of(found, 0)

    assert "Limit: none set" in text
    assert "within" not in text and "over the" not in text


def test_the_section_is_labelled_as_separate_evidence() -> None:
    text = text_of(attempt(), 1)

    assert "evidence only" in text
    assert "separate from explanation feedback and test results" in text
    assert "never changes explanation scores, completion" in text


def test_a_clock_before_the_start_never_reports_negative_time() -> None:
    report = timing_report(attempt(), now(-5))

    assert report.open_elapsed == timedelta(0)


@pytest.mark.parametrize("bad", [0, -3])
def test_a_limit_must_be_a_positive_number_of_minutes(bad: int) -> None:
    with pytest.raises(TimingError, match="positive"):
        validate_limit(True, bad)


def test_a_limit_needs_timing_to_be_chosen() -> None:
    with pytest.raises(TimingError, match="--timed"):
        validate_limit(False, 30)
    validate_limit(False, None)
    validate_limit(True, None)
    validate_limit(True, 30)


@pytest.mark.parametrize("bad", ["soon", 0, -4, True, 2.5])
def test_a_damaged_limit_in_the_journal_is_ignored_not_trusted(bad: object) -> None:
    found = build_history([started_record(limit=bad)]).attempts[0]

    assert found.limit_minutes is None
