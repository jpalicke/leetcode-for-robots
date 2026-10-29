# ABOUTME: Derives attempts, status and progress from journal events and attempt files.
# ABOUTME: Everything here is computed fresh on each call; nothing derived is stored.

import hashlib
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Literal

from practice.journal import Journal
from practice.rubric import ExplanationScores, RubricError

JOURNAL_FILE = "journal.jsonl"
ATTEMPTS_DIR = "attempts"
CODE_FILE = "solution.py"

Status = Literal["in_progress", "passed", "stale"]
STATUS_LABELS: dict[str, str] = {
    "in_progress": "in progress",
    "passed": "passed locally",
    "stale": "stale after edit",
}
_RANK: dict[str, int] = {"in_progress": 0, "stale": 1, "passed": 2}


class AttemptError(Exception):
    """An attempt cannot be found, created or recorded against."""


@dataclass
class Attempt:
    attempt_id: str
    platform: str
    problem_id: str
    title: str
    language: str
    mode: str
    timed: bool
    started_at: str
    events: list[dict[str, Any]] = field(default_factory=list)  # Starts with the start.
    finished_at: str | None = None
    review: bool = False  # Started as a blank spaced review of an earlier pass.
    limit_minutes: int | None = None  # The optional limit chosen with timing.


@dataclass
class History:
    attempts: list[Attempt]
    notices: list[str]  # Problems found while reading; shown, never hidden.
    records: list[dict[str, Any]] = field(default_factory=list)  # All, in order.


@dataclass(frozen=True)
class ExplanationView:
    """One recorded explanation assessment, judged against the code as it is now."""

    event_id: str
    at: str
    sequence: int  # 1 for the initial assessment, then in journal order.
    scores: ExplanationScores
    evidence: str
    feedback: str
    coaching: str | None  # Optimization coaching: separate, never scored.
    code_sha256: str | None
    is_current: bool  # The assessed code is the code as it is now.
    code_passed: bool  # A local run passed on exactly the assessed code.

    @property
    def label(self) -> str:
        return "initial" if self.sequence == 1 else f"revision {self.sequence - 1}"


@dataclass
class AttemptView:
    attempt: Attempt
    code_path: Path
    current_sha256: str | None  # None when the attempt file cannot be read.
    status: Status
    latest_run: dict[str, Any] | None
    latest_pass: dict[str, Any] | None
    verdict: dict[str, Any] | None
    explanations: list[ExplanationView] = field(default_factory=list)

    @property
    def latest_explanation(self) -> ExplanationView | None:
        return self.explanations[-1] if self.explanations else None


@dataclass
class ProblemSummary:
    platform: str
    problem_id: str
    title: str
    status: Status
    attempts: list[AttemptView]
    verdict: dict[str, Any] | None


def journal_for(practice_dir: Path) -> Journal:
    return Journal(practice_dir / JOURNAL_FILE)


def attempt_code_path(
    practice_dir: Path, platform: str, problem_id: str, attempt_id: str
) -> Path:
    return (
        practice_dir
        / ATTEMPTS_DIR
        / f"{platform}-{problem_id}"
        / attempt_id
        / CODE_FILE
    )


def load_history(practice_dir: Path) -> History:
    contents = journal_for(practice_dir).read()
    history = build_history(contents.records)
    reported = [
        f"{JOURNAL_FILE} line {problem.line_number}: {problem.message}"
        for problem in contents.problems
    ]
    history.notices[:0] = reported
    return history


def build_history(records: list[dict[str, Any]]) -> History:
    attempts: dict[str, Attempt] = {}
    notices: list[str] = []
    for record in records:
        attempt_id = record.get("attempt_id")
        if record["type"] == "attempt_started":
            if not isinstance(attempt_id, str):
                notices.append("an attempt_started event has no attempt_id; ignored")
                continue
            if attempt_id in attempts:
                notices.append(
                    f"attempt {attempt_id} was started twice; kept the first"
                )
                continue
            attempts[attempt_id] = Attempt(
                attempt_id=attempt_id,
                platform=record["platform"],
                problem_id=record["problem_id"],
                title=record.get("title", ""),
                language=record["language"],
                mode=record["mode"],
                timed=record["timed"],
                started_at=record["at"],
                events=[record],
                review=record.get("review") is True,
                limit_minutes=_limit_minutes(record),
            )
        elif attempt_id is not None:
            attempt = attempts.get(attempt_id)
            if attempt is None:
                notices.append(
                    f"event {record['event_id']} ({record['type']}) refers to "
                    f"unknown attempt {attempt_id}"
                )
                continue
            if record["type"] == "explanation_assessment":
                try:
                    ExplanationScores.from_record(record)
                except RubricError as error:
                    notices.append(
                        f"event {record['event_id']} (explanation_assessment) "
                        f"has an invalid score ({error}); ignored"
                    )
                    continue
            attempt.events.append(record)
            if record["type"] == "attempt_finished":
                attempt.finished_at = attempt.finished_at or record["at"]
    return History(list(attempts.values()), notices, records)


def _limit_minutes(record: dict[str, Any]) -> int | None:
    """The chosen limit, or None when absent or not a positive whole number."""
    limit = record.get("limit_minutes")
    valid = isinstance(limit, int) and not isinstance(limit, bool) and limit > 0
    return limit if valid else None


def find_attempt(history: History, text: str) -> Attempt:
    """Find an attempt by exact ID or by a prefix that matches only one."""
    exact = [a for a in history.attempts if a.attempt_id == text]
    if exact:
        return exact[0]
    matches = [a for a in history.attempts if text and a.attempt_id.startswith(text)]
    if not matches:
        raise AttemptError(f"no attempt matches {text!r}; see: practice attempt list")
    if len(matches) > 1:
        raise AttemptError(f"{text!r} is ambiguous; it matches {len(matches)} attempts")
    return matches[0]


def latest_unfinished(
    history: History, platform: str | None, problem_id: str | None
) -> Attempt | None:
    for attempt in reversed(history.attempts):
        if attempt.finished_at is not None:
            continue
        if platform is not None and (attempt.platform, attempt.problem_id) != (
            platform,
            problem_id,
        ):
            continue
        return attempt
    return None


def view_attempt(attempt: Attempt, practice_dir: Path) -> AttemptView:
    code_path = attempt_code_path(
        practice_dir, attempt.platform, attempt.problem_id, attempt.attempt_id
    )
    current = hash_file(code_path)
    runs = [e for e in attempt.events if e["type"] == "test_run"]
    passes = [e for e in runs if e["status"] == "passed"]
    runs_on_current = [e for e in runs if current and e["code_sha256"] == current]

    status: Status
    if runs_on_current:
        passed = runs_on_current[-1]["status"] == "passed"
        status = "passed" if passed else "in_progress"
    elif passes:
        status = "stale"  # A pass exists, but never for the code as it is now.
    else:
        status = "in_progress"
    verdicts = [e for e in attempt.events if e["type"] == "platform_verdict"]
    return AttemptView(
        attempt=attempt,
        code_path=code_path,
        current_sha256=current,
        status=status,
        latest_run=runs[-1] if runs else None,
        latest_pass=passes[-1] if passes else None,
        verdict=verdicts[-1] if verdicts else None,
        explanations=_explanation_views(attempt, current),
    )


def _explanation_views(attempt: Attempt, current: str | None) -> list[ExplanationView]:
    """Every assessment in journal order, so revisions are never overwritten."""
    passed_code = {
        e["code_sha256"]
        for e in attempt.events
        if e["type"] == "test_run" and e["status"] == "passed"
    }
    assessments = [e for e in attempt.events if e["type"] == "explanation_assessment"]
    return [
        ExplanationView(
            event_id=event["event_id"],
            at=event["at"],
            sequence=number,
            scores=ExplanationScores.from_record(event),
            evidence=event.get("evidence", ""),
            feedback=event.get("feedback", ""),
            coaching=event.get("coaching"),
            code_sha256=event.get("code_sha256"),
            is_current=current is not None and event.get("code_sha256") == current,
            code_passed=event.get("code_sha256") in passed_code,
        )
        for number, event in enumerate(assessments, start=1)
    ]


def hash_file(path: Path) -> str | None:
    try:
        return hashlib.sha256(path.read_bytes()).hexdigest()
    except OSError:
        return None


def summarize_problems(views: list[AttemptView]) -> list[ProblemSummary]:
    grouped: dict[tuple[str, str], list[AttemptView]] = {}
    for view in views:
        key = (view.attempt.platform, view.attempt.problem_id)
        grouped.setdefault(key, []).append(view)
    summaries = []
    for (platform, problem_id), group in grouped.items():
        verdicts = [v.verdict for v in reversed(group) if v.verdict is not None]
        summaries.append(
            ProblemSummary(
                platform=platform,
                problem_id=problem_id,
                title=group[-1].attempt.title,
                status=max((v.status for v in group), key=_RANK.__getitem__),
                attempts=group,
                verdict=max(verdicts, key=lambda e: e["at"]) if verdicts else None,
            )
        )
    return summaries
