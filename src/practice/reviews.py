# ABOUTME: Derives the spaced review schedule from journal events; nothing is stored.
# ABOUTME: Ladder, eligibility, skip and reschedule rules live here and only here.

from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from typing import Any, Literal

from practice.history import (
    Attempt,
    AttemptView,
    History,
    journal_for,
    load_history,
    view_attempt,
)
from practice.journal import JournalError

# The approved starting gaps in days. Each step up the ladder is one entry later.
GAP_DAYS: tuple[int, ...] = (1, 3, 7, 14, 30)
TOP_RUNG = len(GAP_DAYS) - 1
# A core explanation score (out of 10) below this shows the idea was not understood.
EXPLANATION_CORE_THRESHOLD = 7

REVIEW_SKIPPED = "review_skipped"
REVIEW_RESCHEDULED = "review_rescheduled"

Outcome = Literal["advance", "hold", "shorten", "reset"]
Key = tuple[str, str, str]  # Platform, problem ID and language: one review track.


class ReviewError(Exception):
    """A review cannot be found or recorded against."""


@dataclass(frozen=True)
class ReviewItem:
    platform: str
    problem_id: str
    title: str
    language: str
    rung: int  # Index into GAP_DAYS.
    gap_days: int
    practiced_on: date  # The day of the pass that anchors the schedule.
    due_on: date
    open_attempt_id: str | None  # An unfinished review attempt that has not passed.
    adjusted: str | None  # "skipped" or "rescheduled" when the learner moved it.

    @property
    def key(self) -> Key:
        return (self.platform, self.problem_id, self.language)

    def is_due(self, today: date) -> bool:
        return self.due_on <= today


@dataclass(frozen=True)
class ReviewSchedule:
    items: list[ReviewItem]
    notices: list[str]  # Problems found while reading; shown, never hidden.

    def due(self, today: date) -> list[ReviewItem]:
        return [item for item in self.items if item.is_due(today)]

    def upcoming(self, today: date) -> list[ReviewItem]:
        return [item for item in self.items if not item.is_due(today)]

    def find(self, platform: str, problem_id: str, language: str) -> ReviewItem | None:
        key = (platform, problem_id, language)
        return next((item for item in self.items if item.key == key), None)


def load_schedule(practice_dir: Path) -> ReviewSchedule:
    """Read the journal and work out every review. Writes nothing."""
    return build_schedule(load_history(practice_dir), practice_dir)


def build_schedule(history: History, practice_dir: Path) -> ReviewSchedule:
    """Fold the journal in order into one track per platform, problem and language.

    A problem becomes review-eligible when an attempt of it has a passing local run.
    The first such attempt starts the track at the shortest gap. After that only
    attempts started as reviews count: each moves the track up or down the ladder
    by how independently it passed. Skips and reschedules move the date, never the
    rung. Every date is counted from the day of the pass, not the day it was due.
    """
    notices = list(history.notices)
    first_passes = _first_passes(history)
    tracks: dict[Key, _Track] = {}
    for record in history.records:
        kind = record["type"]
        if record["event_id"] in first_passes:
            attempt = first_passes[record["event_id"]]
            _apply_pass(tracks, history, attempt, record, practice_dir)
        elif kind in (REVIEW_SKIPPED, REVIEW_RESCHEDULED):
            problem = _apply_adjustment(tracks, record)
            if problem:
                notices.append(
                    f"event {record['event_id']} ({kind}) {problem}; ignored"
                )
    items = [_item(track, history) for track in tracks.values()]
    items.sort(key=lambda i: (i.due_on, i.platform, len(i.problem_id), i.problem_id))
    return ReviewSchedule(items, notices)


def record_skip(practice_dir: Path, item: ReviewItem) -> None:
    """Postpone a review by its current gap. Rung and scores stay as they are."""
    _require_scheduled(practice_dir, item)
    _append(practice_dir, REVIEW_SKIPPED, **_identity(item))


def record_reschedule(practice_dir: Path, item: ReviewItem, due_on: date) -> None:
    """Move a review to a chosen date. The rung and every score stay as they are."""
    _require_scheduled(practice_dir, item)
    _append(
        practice_dir,
        REVIEW_RESCHEDULED,
        due_on=due_on.isoformat(),
        **_identity(item),
    )


# Folding


@dataclass
class _Track:
    platform: str
    problem_id: str
    title: str
    language: str
    rung: int
    anchor_position: int  # Where the anchoring attempt sits in the history.
    practiced_on: date
    due_on: date
    adjusted: str | None = None


def _first_passes(history: History) -> dict[str, Attempt]:
    """Map the event ID of each attempt's first passing run to that attempt."""
    found: dict[str, Attempt] = {}
    for attempt in history.attempts:
        for event in attempt.events:
            if event["type"] == "test_run" and event["status"] == "passed":
                found[event["event_id"]] = attempt
                break
    return found


def _apply_pass(
    tracks: dict[Key, _Track],
    history: History,
    attempt: Attempt,
    run: dict[str, Any],
    practice_dir: Path,
) -> None:
    key = (attempt.platform, attempt.problem_id, attempt.language)
    track = tracks.get(key)
    if track is not None and not attempt.review:
        return  # An ordinary later attempt does not move the ladder.
    if track is None:
        rung = 0
    else:
        view = view_attempt(attempt, practice_dir)
        rung = _move(track.rung, judge_pass(attempt, view, run["event_id"]))
    practiced_on = _day(run["at"])
    tracks[key] = _Track(
        platform=attempt.platform,
        problem_id=attempt.problem_id,
        title=attempt.title,
        language=attempt.language,
        rung=rung,
        anchor_position=history.attempts.index(attempt),
        practiced_on=practiced_on,
        due_on=practiced_on + timedelta(days=GAP_DAYS[rung]),
    )


def judge_pass(attempt: Attempt, view: AttemptView, pass_event_id: str) -> Outcome:
    """How a passing review should move the ladder.

    Only help given before the pass counts, since it shapes how the pass was won.
    A reveal or a weak explanation sends the review back to the shortest gap. Hints
    shorten it by a step. Concept help, or a pass that has gone stale after an
    edit, holds it. Anything else is an independent success.
    """
    kinds: set[str] = set()
    for event in attempt.events:
        if event["event_id"] == pass_event_id:
            break
        if event["type"] == "assistance":
            kinds.add(event["kind"])
    if "reveal" in kinds or _misunderstood(view):
        return "reset"
    if "hint" in kinds:
        return "shorten"
    if "concept" in kinds or view.status != "passed":
        return "hold"
    return "advance"


def _misunderstood(view: AttemptView) -> bool:
    for explanation in reversed(view.explanations):
        total = explanation.scores.core_total
        if total is not None:
            return total < EXPLANATION_CORE_THRESHOLD
    return False  # Nothing was fully assessed, which is never held against anyone.


def _move(rung: int, outcome: Outcome) -> int:
    if outcome == "advance":
        return min(rung + 1, TOP_RUNG)
    if outcome == "shorten":
        return max(rung - 1, 0)
    if outcome == "reset":
        return 0
    return rung


def _apply_adjustment(tracks: dict[Key, _Track], record: dict[str, Any]) -> str:
    """Move a track's date. Returns what is wrong with the record, or nothing."""
    key = tuple(record.get(name) for name in ("platform", "problem_id", "language"))
    if not all(isinstance(part, str) and part for part in key):
        return "does not name a platform, problem and language"
    track = tracks.get((str(key[0]), str(key[1]), str(key[2])))
    if track is None:
        return "refers to a problem with no review scheduled"
    if record["type"] == REVIEW_SKIPPED:
        track.due_on = _day(record["at"]) + timedelta(days=GAP_DAYS[track.rung])
        track.adjusted = "skipped"
        return ""
    try:
        track.due_on = date.fromisoformat(str(record.get("due_on")))
    except ValueError:
        return f"has an invalid due_on {record.get('due_on')!r}"
    track.adjusted = "rescheduled"
    return ""


def _item(track: _Track, history: History) -> ReviewItem:
    return ReviewItem(
        platform=track.platform,
        problem_id=track.problem_id,
        title=track.title,
        language=track.language,
        rung=track.rung,
        gap_days=GAP_DAYS[track.rung],
        practiced_on=track.practiced_on,
        due_on=track.due_on,
        open_attempt_id=_open_review_attempt(track, history),
        adjusted=track.adjusted,
    )


def _open_review_attempt(track: _Track, history: History) -> str | None:
    for position in range(len(history.attempts) - 1, track.anchor_position, -1):
        attempt = history.attempts[position]
        same = (attempt.platform, attempt.problem_id, attempt.language) == (
            track.platform,
            track.problem_id,
            track.language,
        )
        passed = any(
            e["type"] == "test_run" and e["status"] == "passed" for e in attempt.events
        )
        if same and attempt.review and attempt.finished_at is None and not passed:
            return attempt.attempt_id
    return None


def _day(timestamp: str) -> date:
    return datetime.fromisoformat(timestamp).astimezone(UTC).date()


def _identity(item: ReviewItem) -> dict[str, str]:
    return {
        "platform": item.platform,
        "problem_id": item.problem_id,
        "language": item.language,
    }


def _require_scheduled(practice_dir: Path, item: ReviewItem) -> None:
    if load_schedule(practice_dir).find(*item.key) is None:
        raise ReviewError(
            f"no review is scheduled for {item.platform} {item.problem_id} "
            f"({item.language}); pass the problem locally first"
        )


def _append(practice_dir: Path, event_type: str, **fields: object) -> None:
    try:
        journal_for(practice_dir).append(event_type, **fields)
    except JournalError as error:
        raise ReviewError(str(error)) from error


def describe_review(item: ReviewItem) -> str:
    """One line for a review: what it is, when it is due and where it sits."""
    line = (
        f"{item.platform} {item.problem_id}  {item.title}  ({item.language})  "
        f"due {item.due_on.isoformat()}  rung {item.rung + 1} of {len(GAP_DAYS)} "
        f"({item.gap_days} day gap)"
    )
    if item.adjusted:
        line += f"  {item.adjusted}"
    return line
