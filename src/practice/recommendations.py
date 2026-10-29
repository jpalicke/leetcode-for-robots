# ABOUTME: Recommends what to practice next from the curriculum and learner evidence.
# ABOUTME: Pure and deterministic: reads the journal, writes nothing, fixed priority.

from collections.abc import Callable
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any

from practice.catalog import Catalog, Entry
from practice.curriculum import Curriculum, Placement
from practice.history import Attempt, AttemptView, History, load_history, view_attempt
from practice.reviews import (
    EXPLANATION_CORE_THRESHOLD,
    assistance_before,
    build_schedule,
    first_pass,
    judge_pass,
    latest_core_total,
)

MAX_ALTERNATIVES = 3  # The primary recommendation plus at most this many others.

ReadyCheck = Callable[[str, str], bool]  # (platform, problem id) -> has a ready package


@dataclass(frozen=True)
class Reason:
    code: str
    phrase: str  # The only wording a learner ever sees for this reason.


# The one list of candidate sources. Its order is the priority order: a problem
# that qualifies under several reasons is shown under the first one.
RESUME = Reason("resume", "unfinished attempt to resume")
DUE_REVIEW = Reason("due_review", "due review")
PREREQUISITE_GAP = Reason("prerequisite_gap", "prerequisite gap")
NEXT_OBJECTIVE = Reason("next_objective", "next curriculum objective")
REASONS: tuple[Reason, ...] = (RESUME, DUE_REVIEW, PREREQUISITE_GAP, NEXT_OBJECTIVE)

# Within one reason the order is fixed: resume newest attempt first, due reviews by
# due date then problem, gaps and objectives in curriculum order. No randomness.

_HELP_WORDS = {"hint": "hint", "concept": "concept explanation", "reveal": "reveal"}


@dataclass(frozen=True)
class ProblemEvidence:
    """What the journal shows about one problem, in plain words.

    Mastery is an independent pass (no help before it, code unchanged since) with a
    not-low explanation, or a successful blank review. A passing test run alone is
    never mastery. A later review that needed help withdraws it.
    """

    status: str  # new, attempted, stale_pass, passed_with_help, independent, mastered
    independent: bool
    mastered: bool
    explanation: str  # none, ok or low
    blank_review_passed: bool
    text: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "independent": self.independent,
            "mastered": self.mastered,
            "explanation": self.explanation,
            "text": self.text,
        }


@dataclass(frozen=True)
class Candidate:
    platform: str
    problem_id: str
    title: str
    difficulty: str
    reason: str  # A Reason code.
    reason_phrase: str
    detail: str  # One plain sentence: never a technique or a curriculum key.
    action: str  # start, resume or review
    attempt_id: str | None
    command: str
    evidence: ProblemEvidence

    @property
    def label(self) -> str:
        """Neutral by design: the title and difficulty, nothing else."""
        return f"{self.title} [{self.difficulty}]"

    def to_dict(self) -> dict[str, Any]:
        return {
            "platform": self.platform,
            "problem_id": self.problem_id,
            "label": self.label,
            "title": self.title,
            "difficulty": self.difficulty,
            "reason": self.reason,
            "reason_text": self.reason_phrase,
            "detail": self.detail,
            "action": self.action,
            "attempt_id": self.attempt_id,
            "command": self.command,
            "evidence": self.evidence.to_dict(),
        }


@dataclass(frozen=True)
class Recommendation:
    candidates: tuple[Candidate, ...]  # The primary first, then the alternatives.
    pending: int  # Unsolved curriculum problems with no ready exercise yet.
    message: str  # Why there is nothing to recommend; empty otherwise.

    @property
    def primary(self) -> Candidate | None:
        return self.candidates[0] if self.candidates else None

    @property
    def alternatives(self) -> tuple[Candidate, ...]:
        return self.candidates[1:]


# Evidence


@dataclass(frozen=True)
class _Facts:
    attempt: Attempt
    view: AttemptView
    run: dict[str, Any] | None  # The attempt's first passing run.
    help: list[str]  # Kinds of help delivered before that pass.

    @property
    def counts(self) -> bool:
        """The pass is for the code as it is now."""
        return self.run is not None and self.view.status == "passed"

    @property
    def independent(self) -> bool:
        return self.counts and not self.help

    @property
    def core(self) -> int | None:
        return latest_core_total(self.view)


def problem_evidence(
    history: History, practice_dir: Path, platform: str, problem_id: str
) -> ProblemEvidence:
    attempts = [
        a
        for a in history.attempts
        if (a.platform, a.problem_id) == (platform, problem_id)
    ]
    if not attempts:
        return ProblemEvidence("new", False, False, "none", False, "No attempts yet.")
    facts = [_facts(a, practice_dir) for a in attempts]
    independent = [f for f in facts if f.independent]
    reviews = [f for f in facts if f.attempt.review and f.run is not None]
    blank_review = bool(reviews) and _outcome(reviews[-1]) == "advance"
    solid = any(
        f.core is not None and f.core >= EXPLANATION_CORE_THRESHOLD for f in independent
    )
    mastered = blank_review if reviews else solid
    passing = independent or [f for f in facts if f.counts]
    shown = passing[-1] if passing else None
    explanation = "none"
    if shown is not None and shown.core is not None:
        low = shown.core < EXPLANATION_CORE_THRESHOLD
        explanation = "low" if low else "ok"
    if mastered:
        status = "mastered"
    elif independent:
        status = "independent"
    elif shown is not None:
        status = "passed_with_help"
    elif any(f.run is not None for f in facts):
        status = "stale_pass"
    else:
        status = "attempted"
    text = _evidence_text(
        status, mastered, blank_review, bool(reviews), explanation, shown
    )
    return ProblemEvidence(
        status, bool(independent), mastered, explanation, blank_review, text
    )


def _facts(attempt: Attempt, practice_dir: Path) -> _Facts:
    run = first_pass(attempt)
    helped = assistance_before(attempt, run["event_id"]) if run else []
    return _Facts(attempt, view_attempt(attempt, practice_dir), run, helped)


def _outcome(facts: _Facts) -> str:
    assert facts.run is not None
    return judge_pass(facts.attempt, facts.view, facts.run["event_id"])


def _evidence_text(
    status: str,
    mastered: bool,
    blank_review: bool,
    reviewed: bool,
    explanation: str,
    shown: _Facts | None,
) -> str:
    if mastered and blank_review:
        return "Mastered: a blank review passed independently."
    if mastered:
        return "Mastered: passed independently and the explanation scored well."
    if status == "independent":
        if explanation == "low":
            return (
                "Passed independently, but the explanation scored low. "
                "Not yet mastered."
            )
        if reviewed:
            return (
                "Passed independently once, but the latest blank review needed "
                "help. Not yet mastered."
            )
        return (
            "Passed independently. Not yet mastered: it needs a well-scored "
            "explanation or a successful blank review."
        )
    if status == "passed_with_help":
        assert shown is not None
        return f"Passed with help ({_help_text(shown.help)}). Not independent yet."
    if status == "stale_pass":
        return (
            "A pass is on record, but the code changed since. It does not count "
            "until the tests pass again."
        )
    return "Attempted without a local pass yet."


def _help_text(kinds: list[str]) -> str:
    parts = []
    for kind in dict.fromkeys(kinds):
        count = kinds.count(kind)
        word = _HELP_WORDS.get(kind, kind)
        parts.append(f"{count} {word}{'' if count == 1 else 's'}")
    return ", ".join(parts)


# Candidates


def build_recommendation(
    practice_dir: Path,
    catalog: Catalog,
    curriculum: Curriculum,
    ready: ReadyCheck,
    today: date,
) -> Recommendation:
    """Rank what to practice next. Reads the journal; nothing is written."""
    history = load_history(practice_dir)
    entries = {(e.platform, str(e.frontend_question_id)): e for e in catalog.entries}
    evidence_cache: dict[tuple[str, str], ProblemEvidence] = {}

    def evidence_for(entry: Entry) -> ProblemEvidence:
        key = (entry.platform, str(entry.frontend_question_id))
        if key not in evidence_cache:
            evidence_cache[key] = problem_evidence(
                history, practice_dir, key[0], key[1]
            )
        return evidence_cache[key]

    def usable(entry: Entry) -> bool:
        return ready(entry.platform, str(entry.frontend_question_id))

    def solved(entry: Entry) -> bool:
        return evidence_for(entry).independent

    found: dict[tuple[str, str], Candidate] = {}

    def add(
        entry: Entry,
        reason: Reason,
        detail: str,
        action: str = "start",
        attempt_id: str | None = None,
    ) -> None:
        key = (entry.platform, str(entry.frontend_question_id))
        if key in found or not usable(entry):
            return  # The highest priority reason wins; pending is never offered.
        found[key] = _candidate(
            entry, reason, detail, action, attempt_id, evidence_for(entry)
        )

    seen_open: set[tuple[str, str]] = set()
    for attempt in reversed(history.attempts):
        key = (attempt.platform, attempt.problem_id)
        entry = entries.get(key)
        if attempt.finished_at is None and first_pass(attempt) is None and entry:
            if key not in seen_open:
                seen_open.add(key)
                add(
                    entry,
                    RESUME,
                    "You have an attempt open for this problem.",
                    "resume",
                    attempt.attempt_id,
                )

    for item in build_schedule(history, practice_dir).due(today):
        entry = entries.get((item.platform, item.problem_id))
        if entry is not None:
            add(
                entry,
                DUE_REVIEW,
                f"A blank review was due on {item.due_on.isoformat()}.",
                "review",
            )

    by_concept: dict[str, list[Placement]] = {}
    for placement in curriculum.placements:
        by_concept.setdefault(placement.concept, []).append(placement)

    def concept_done(concept_id: str) -> bool:
        """Solved independently, or waived because nothing in it is ready yet."""
        return all(
            solved(p.problem)
            for p in by_concept.get(concept_id, [])
            if usable(p.problem)
        )

    done = [c.id for c in curriculum.concepts if concept_done(c.id)]
    order = [c.id for c in curriculum.concepts]

    for placement in curriculum.placements:
        tried = evidence_for(placement.problem)
        if tried.status == "new" or tried.independent:
            continue
        for concept_id in sorted(placement.prerequisites, key=order.index):
            if concept_id in done:
                continue
            for earlier in by_concept.get(concept_id, []):
                if not solved(earlier.problem):
                    add(
                        earlier.problem,
                        PREREQUISITE_GAP,
                        f"{curriculum.label_for(concept_id)} builds up to a "
                        "problem you have already tried.",
                    )

    for objective in curriculum.next_objectives(done):
        for problem in objective.problems:
            if not solved(problem):
                add(problem, NEXT_OBJECTIVE, f"It is part of {objective.label}.")

    pending = sum(
        1
        for p in curriculum.placements
        if not usable(p.problem) and not solved(p.problem)
    )
    ranked = tuple(found.values())[: 1 + MAX_ALTERNATIVES]
    message = "" if ranked else _nothing_message(pending)
    return Recommendation(ranked, pending, message)


def _candidate(
    entry: Entry,
    reason: Reason,
    detail: str,
    action: str,
    attempt_id: str | None,
    evidence: ProblemEvidence,
) -> Candidate:
    where = f"{entry.platform} {entry.frontend_question_id}"
    command = {
        "start": f"practice attempt start {where}",
        "resume": f"practice attempt resume {where}",
        "review": f"practice review start {where}",
    }[action]
    return Candidate(
        platform=entry.platform,
        problem_id=str(entry.frontend_question_id),
        title=entry.title,
        difficulty=entry.difficulty,
        reason=reason.code,
        reason_phrase=reason.phrase,
        detail=detail,
        action=action,
        attempt_id=attempt_id,
        command=command,
        evidence=evidence,
    )


def _nothing_message(pending: int) -> str:
    if pending:
        noun = "problem" if pending == 1 else "problems"
        verb = "has" if pending == 1 else "have"
        return (
            f"Nothing to recommend right now: the {pending} curriculum {noun} "
            f"still unsolved {verb} no ready exercise yet."
        )
    return (
        "Nothing to recommend: every available curriculum problem is solved "
        "independently and no review is due. You can still browse and pick any "
        "problem."
    )
