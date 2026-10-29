# ABOUTME: The one source of "now" for every timestamp the practice tool writes.
# ABOUTME: PRACTICE_NOW (an ISO timestamp or date) replaces the real clock for tests.

import os
from datetime import UTC, date, datetime

PRACTICE_NOW_ENV = "PRACTICE_NOW"


class ClockError(Exception):
    """PRACTICE_NOW is set to something that is not an ISO date or timestamp."""


def now() -> datetime:
    """The current time in UTC, or the instant PRACTICE_NOW names."""
    text = os.environ.get(PRACTICE_NOW_ENV, "").strip()
    if not text:
        return datetime.now(UTC)
    try:
        moment = datetime.fromisoformat(text)
    except ValueError as error:
        raise ClockError(
            f"{PRACTICE_NOW_ENV} must be an ISO date or timestamp such as "
            f"2026-11-02T09:30:00Z, got {text!r}"
        ) from error
    if moment.tzinfo is None:
        return moment.replace(tzinfo=UTC)
    return moment.astimezone(UTC)


def today() -> date:
    """Today's date in UTC, the calendar the journal and review dates use."""
    return now().date()
