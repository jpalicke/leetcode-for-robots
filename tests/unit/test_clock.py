# ABOUTME: Unit tests for the single injectable clock behind every timestamp.
# ABOUTME: PRACTICE_NOW is set in the real process environment; nothing is mocked.

from datetime import UTC, date, datetime
from pathlib import Path

import pytest

from practice.clock import PRACTICE_NOW_ENV, ClockError, now, today
from practice.journal import Journal


def test_now_is_the_real_clock_when_the_variable_is_unset(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv(PRACTICE_NOW_ENV, raising=False)

    assert abs((datetime.now(UTC) - now()).total_seconds()) < 5


def test_now_reads_an_iso_timestamp_with_an_offset(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv(PRACTICE_NOW_ENV, "2026-11-02T09:30:00+02:00")

    assert now() == datetime(2026, 11, 2, 7, 30, tzinfo=UTC)
    assert now().tzinfo is UTC


def test_a_timestamp_without_an_offset_is_read_as_utc(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv(PRACTICE_NOW_ENV, "2026-11-02T09:30:00")

    assert now() == datetime(2026, 11, 2, 9, 30, tzinfo=UTC)


def test_a_bare_date_means_the_start_of_that_utc_day(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv(PRACTICE_NOW_ENV, "2026-11-02")

    assert now() == datetime(2026, 11, 2, tzinfo=UTC)
    assert today() == date(2026, 11, 2)


def test_a_bad_value_is_an_error_not_a_silent_fallback(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv(PRACTICE_NOW_ENV, "next tuesday")

    with pytest.raises(ClockError, match="PRACTICE_NOW"):
        now()


def test_an_empty_value_is_treated_as_unset(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(PRACTICE_NOW_ENV, "")

    assert abs((datetime.now(UTC) - now()).total_seconds()) < 5


def test_journal_records_are_stamped_from_the_clock(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setenv(PRACTICE_NOW_ENV, "2026-11-02T09:30:00Z")
    journal = Journal(tmp_path / "journal.jsonl")

    record = journal.append("note")

    assert record["at"] == "2026-11-02T09:30:00.000+00:00"
