# ABOUTME: Unit tests for the recommendation engine: priority, evidence and mastery.
# ABOUTME: Real journal events and attempt files over a small real catalog and map.

import hashlib
import json
from collections.abc import Callable
from datetime import date
from pathlib import Path
from typing import Any

import pytest

from practice.catalog import Catalog, parse_catalog
from practice.curriculum import Curriculum, parse_curriculum
from practice.history import attempt_code_path, journal_for, load_history
from practice.recommendations import (
    MAX_ALTERNATIVES,
    REASONS,
    ProblemEvidence,
    Recommendation,
    build_recommendation,
    problem_evidence,
)
from practice.tutor_policy import find_technique_terms

DAY0 = date(2026, 11, 1)
TITLES = {
    "1": "Alpha Walk",
    "2": "Beta Walk",
    "3": "Gamma Walk",
    "4": "Delta Walk",
    "5": "Epsilon Walk",
}
CONCEPT_WORDS = ("Quartz Craft", "Basalt Craft", "Granite Craft", "Marble Craft")
CONCEPT_IDS = ("quartz", "basalt", "granite", "marble")
NEEDS: dict[str, list[str]] = {
    "quartz": [],
    "basalt": [],
    "granite": ["basalt"],
    "marble": ["quartz", "granite"],
}
PLACED = {"1": "quartz", "2": "basalt", "3": "granite", "4": "marble", "5": "marble"}


def stamp(offset: int, hour: int = 9) -> str:
    return f"{day(offset).isoformat()}T{hour:02d}:00:00Z"


def day(offset: int) -> date:
    return date.fromordinal(DAY0.toordinal() + offset)


def make_catalog() -> Catalog:
    entries = [
        {
            "platform": "leetcode",
            "frontend_question_id": int(pid),
            "question_id": int(pid),
            "title": title,
            "slug": title.lower().replace(" ", "-"),
            "difficulty": "easy" if pid in "12" else "medium",
            "paid_only": False,
        }
        for pid, title in TITLES.items()
    ]
    return parse_catalog(
        {
            "platform": "leetcode",
            "source_url": "https://example.test",
            "fetched_on": "2026-10-28",
            "entries": entries,
        }
    )


def closure(concept: str) -> set[str]:
    found: set[str] = set()
    for parent in NEEDS[concept]:
        found |= {parent} | closure(parent)
    return found


def make_curriculum(catalog: Catalog) -> Curriculum:
    """quartz(1), basalt(2), granite(3, needs basalt), marble(4 and 5)."""
    return parse_curriculum(
        {
            "version": 1,
            "platform": "leetcode",
            "concepts": [
                {"id": c, "name": CONCEPT_WORDS[i], "prerequisites": NEEDS[c]}
                for i, c in enumerate(CONCEPT_IDS)
            ],
            "starters": [1, 2, 3, 4, 5],
            "placements": [
                {
                    "problem_id": int(pid),
                    "concept": concept,
                    "prerequisites": [c for c in CONCEPT_IDS if c in closure(concept)],
                }
                for pid, concept in PLACED.items()
            ],
        },
        catalog,
    )


class Learner:
    """Writes real journal events and attempt files at chosen days."""

    def __init__(self, practice_dir: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        self.practice_dir = practice_dir
        self.monkeypatch = monkeypatch
        self.counter = 0

    def at(self, offset: int, hour: int = 9) -> None:
        self.monkeypatch.setenv("PRACTICE_NOW", stamp(offset, hour))

    def attempt(
        self,
        offset: int,
        problem_id: str = "1",
        *,
        passes: bool = True,
        review: bool = False,
        help: tuple[str, ...] = (),
        explanation: tuple[int, int, int] | None = None,
        edit_after_pass: bool = False,
        finish: bool = False,
    ) -> str:
        self.counter += 1
        attempt_id = f"a{self.counter:03d}"
        self.at(offset)
        journal = journal_for(self.practice_dir)
        path = attempt_code_path(self.practice_dir, "leetcode", problem_id, attempt_id)
        path.parent.mkdir(parents=True)
        path.write_text("def f():\n    return 1\n", encoding="utf-8")
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        started: dict[str, Any] = {
            "attempt_id": attempt_id,
            "platform": "leetcode",
            "problem_id": problem_id,
            "title": TITLES[problem_id],
            "language": "python",
            "mode": "practice",
            "timed": False,
        }
        if review:
            started["review"] = True
        journal.append("attempt_started", **started)
        for kind in help:
            level = 1 if kind == "hint" else None
            journal.append("assistance", attempt_id=attempt_id, kind=kind, level=level)
        if passes:
            journal.append(
                "test_run",
                attempt_id=attempt_id,
                status="passed",
                message="m",
                code_sha256=digest,
            )
        if explanation is not None:
            approach, correctness, time = explanation
            journal.append(
                "explanation_assessment",
                attempt_id=attempt_id,
                approach=approach,
                correctness=correctness,
                time_complexity=time,
                space_complexity=None,
                evidence="e",
                feedback="f",
                code_sha256=digest,
            )
        if edit_after_pass:
            path.write_text("def f():\n    return 2\n", encoding="utf-8")
        if finish:
            journal.append("attempt_finished", attempt_id=attempt_id)
        return attempt_id

    def recommend(
        self,
        offset: int,
        ready: Callable[[str, str], bool] = lambda platform, problem_id: True,
    ) -> Recommendation:
        self.at(offset)
        catalog = make_catalog()
        return build_recommendation(
            self.practice_dir, catalog, make_curriculum(catalog), ready, day(offset)
        )

    def evidence(self, problem_id: str = "1") -> ProblemEvidence:
        self.at(30)
        return problem_evidence(
            load_history(self.practice_dir), self.practice_dir, "leetcode", problem_id
        )


@pytest.fixture
def learner(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Learner:
    return Learner(tmp_path / "learner", monkeypatch)


def order(result: Recommendation) -> list[tuple[str, str]]:
    return [(c.problem_id, c.reason) for c in result.candidates]


def not_one(platform: str, problem_id: str) -> bool:
    return problem_id != "1"


def not_two(platform: str, problem_id: str) -> bool:
    return problem_id != "2"


def nothing_ready(platform: str, problem_id: str) -> bool:
    return False


# Reason vocabulary and priority


def test_the_reason_vocabulary_is_closed_and_in_priority_order() -> None:
    assert [r.code for r in REASONS] == [
        "resume",
        "due_review",
        "prerequisite_gap",
        "next_objective",
    ]
    assert [r.phrase for r in REASONS] == [
        "unfinished attempt to resume",
        "due review",
        "prerequisite gap",
        "next curriculum objective",
    ]


def test_a_brand_new_learner_gets_the_first_objective_with_nothing_recorded(
    learner: Learner,
) -> None:
    result = learner.recommend(0)

    assert result.primary is not None
    assert (result.primary.problem_id, result.primary.reason) == ("1", "next_objective")
    assert result.primary.action == "start"
    assert result.primary.evidence.status == "new"
    assert not learner.practice_dir.exists()
    assert result.message == ""


def test_the_ranked_list_is_one_primary_and_a_short_set_of_alternatives(
    learner: Learner,
) -> None:
    result = learner.recommend(0)

    assert len(result.alternatives) <= MAX_ALTERNATIVES
    assert [c.problem_id for c in result.alternatives] == ["2"]
    assert result.candidates[0] is result.primary


def test_an_unfinished_attempt_beats_a_due_review(learner: Learner) -> None:
    learner.attempt(0, "1")
    open_id = learner.attempt(1, "2", passes=False)

    result = learner.recommend(1)

    assert order(result)[0] == ("2", "resume")
    assert result.candidates[0].attempt_id == open_id
    assert result.candidates[0].action == "resume"
    assert ("1", "due_review") in order(result)


def test_an_unfinished_attempt_that_already_passed_is_not_resumed(
    learner: Learner,
) -> None:
    learner.attempt(0, "1")

    assert ("1", "resume") not in order(learner.recommend(0))


def test_a_due_review_beats_the_next_objective(learner: Learner) -> None:
    learner.attempt(0, "1")

    result = learner.recommend(1)

    assert order(result)[0] == ("1", "due_review")
    assert result.primary is not None and result.primary.action == "review"
    assert ("2", "next_objective") in order(result)


def test_a_review_that_is_not_yet_due_is_not_recommended(learner: Learner) -> None:
    learner.attempt(0, "1")

    assert all(c.reason != "due_review" for c in learner.recommend(0).candidates)


def test_a_prerequisite_gap_beats_the_next_objective(learner: Learner) -> None:
    # Problem 3 needs the basalt objective (problem 2), which is not solved. The
    # first objective (problem 1) would otherwise come first.
    learner.attempt(0, "3", passes=False, finish=True)

    result = learner.recommend(0)

    assert order(result)[:2] == [("2", "prerequisite_gap"), ("1", "next_objective")]
    assert "Objective 2" in result.candidates[0].detail


def test_each_problem_appears_once_under_its_highest_priority_reason(
    learner: Learner,
) -> None:
    learner.attempt(0, "3", passes=False, finish=True)

    ids = [c.problem_id for c in learner.recommend(0).candidates]

    assert len(ids) == len(set(ids))


def test_curriculum_order_breaks_ties_the_same_way_every_time(
    learner: Learner,
) -> None:
    first = order(learner.recommend(0))

    assert all(order(learner.recommend(0)) == first for _ in range(5))
    assert [pid for pid, _ in first] == ["1", "2"]


def test_a_problem_solved_independently_is_not_recommended_again(
    learner: Learner,
) -> None:
    learner.attempt(0, "1", finish=True)

    result = learner.recommend(0)

    assert ("1", "next_objective") not in order(result)
    assert order(result)[0] == ("2", "next_objective")


def test_solving_a_prerequisite_unlocks_the_next_objective(learner: Learner) -> None:
    learner.attempt(0, "1", finish=True)
    learner.attempt(0, "2", finish=True)

    assert order(learner.recommend(0)) == [("3", "next_objective")]


def test_every_problem_of_an_objective_must_be_solved_before_its_dependents(
    learner: Learner,
) -> None:
    for pid in ("1", "2", "3", "4"):
        learner.attempt(0, pid, finish=True)

    assert order(learner.recommend(0)) == [("5", "next_objective")]


def test_a_pass_with_help_is_not_independent_so_the_problem_returns(
    learner: Learner,
) -> None:
    learner.attempt(0, "1", help=("hint", "hint"), finish=True)

    result = learner.recommend(0)

    assert order(result)[0] == ("1", "next_objective")
    assert result.candidates[0].evidence.status == "passed_with_help"
    assert "2 hints" in result.candidates[0].evidence.text


def test_nothing_unsolved_yields_a_plain_message_and_no_candidates(
    learner: Learner,
) -> None:
    for pid in TITLES:
        learner.attempt(0, pid, finish=True)

    result = learner.recommend(0)

    assert result.candidates == ()
    assert result.primary is None
    assert "Nothing to recommend" in result.message
    assert "every available" in result.message


# Pending packages


def test_a_problem_without_a_ready_package_is_never_recommended(
    learner: Learner,
) -> None:
    result = learner.recommend(0, ready=not_one)

    assert all(c.problem_id != "1" for c in result.candidates)
    assert result.pending == 1


def test_a_concept_with_no_ready_problem_does_not_stall_what_comes_after(
    learner: Learner,
) -> None:
    result = learner.recommend(0, ready=not_one)

    assert order(result)[0] == ("2", "next_objective")


def test_when_everything_left_is_pending_the_message_says_so(learner: Learner) -> None:
    result = learner.recommend(0, ready=nothing_ready)

    assert result.candidates == ()
    assert "5 curriculum problems" in result.message
    assert "no ready exercise" in result.message


def test_a_pending_unfinished_attempt_is_not_recommended_to_resume(
    learner: Learner,
) -> None:
    learner.attempt(0, "2", passes=False)

    result = learner.recommend(0, ready=not_two)

    assert all(c.problem_id != "2" for c in result.candidates)


# Evidence and mastery


def test_no_attempt_is_new_and_an_unpassed_attempt_is_attempted(
    learner: Learner,
) -> None:
    assert learner.evidence().status == "new"
    learner.attempt(0, "1", passes=False)
    assert learner.evidence().status == "attempted"


def test_a_pass_alone_is_independent_but_not_mastery(learner: Learner) -> None:
    learner.attempt(0, "1")

    evidence = learner.evidence()

    assert evidence.independent
    assert not evidence.mastered
    assert evidence.status == "independent"
    assert "Not yet mastered" in evidence.text


def test_an_independent_pass_with_a_not_low_explanation_is_mastery(
    learner: Learner,
) -> None:
    learner.attempt(0, "1", explanation=(3, 3, 1))

    evidence = learner.evidence()

    assert evidence.mastered
    assert evidence.status == "mastered"
    assert evidence.explanation == "ok"


def test_a_low_explanation_blocks_mastery(learner: Learner) -> None:
    learner.attempt(0, "1", explanation=(1, 1, 1))

    evidence = learner.evidence()

    assert evidence.independent
    assert not evidence.mastered
    assert evidence.explanation == "low"
    assert "scored low" in evidence.text


def test_a_hinted_pass_with_a_good_explanation_is_not_mastery(
    learner: Learner,
) -> None:
    learner.attempt(0, "1", help=("hint",), explanation=(4, 4, 2))

    evidence = learner.evidence()

    assert not evidence.independent
    assert not evidence.mastered
    assert evidence.status == "passed_with_help"


@pytest.mark.parametrize("kind", ["concept", "reveal"])
def test_any_assistance_before_the_pass_means_it_is_not_independent(
    learner: Learner, kind: str
) -> None:
    learner.attempt(0, "1", help=(kind,))

    assert not learner.evidence().independent


def test_a_successful_blank_review_is_mastery(learner: Learner) -> None:
    learner.attempt(0, "1")
    learner.attempt(2, "1", review=True)

    evidence = learner.evidence()

    assert evidence.mastered
    assert evidence.blank_review_passed
    assert "blank review" in evidence.text


def test_a_helped_review_is_not_mastery(learner: Learner) -> None:
    learner.attempt(0, "1")
    learner.attempt(2, "1", review=True, help=("hint",))

    assert not learner.evidence().mastered


def test_a_pass_whose_code_was_edited_afterwards_is_stale(learner: Learner) -> None:
    learner.attempt(0, "1", edit_after_pass=True)

    evidence = learner.evidence()

    assert evidence.status == "stale_pass"
    assert not evidence.independent


def test_a_later_helped_pass_withdraws_mastery(learner: Learner) -> None:
    learner.attempt(0, "1", explanation=(4, 4, 2))
    learner.attempt(5, "1", review=True, help=("reveal",))

    evidence = learner.evidence()

    assert evidence.independent  # It was solved independently once.
    assert not evidence.mastered


# Privacy and labels


def test_labels_are_only_a_title_and_a_difficulty(learner: Learner) -> None:
    learner.attempt(0, "1")
    result = learner.recommend(1)

    assert result.candidates
    for candidate in result.candidates:
        assert candidate.label == f"{candidate.title} [{candidate.difficulty}]"


def test_no_visible_text_names_a_concept_or_a_technique(learner: Learner) -> None:
    learner.attempt(0, "3", help=("hint",), finish=True)
    learner.attempt(0, "1")
    result = learner.recommend(1)
    text = (
        json.dumps(
            [
                [c.label, c.detail, c.evidence.text, c.reason_phrase, c.command]
                for c in result.candidates
            ]
        )
        + result.message
    )

    assert result.candidates
    assert find_technique_terms(text) == []
    for word in (*CONCEPT_WORDS, *CONCEPT_IDS):
        assert word.lower() not in text.lower()


def test_recommending_writes_nothing_to_the_journal(learner: Learner) -> None:
    learner.attempt(0, "1")
    journal = learner.practice_dir / "journal.jsonl"
    before = journal.read_bytes()

    learner.recommend(1)

    assert journal.read_bytes() == before
    assert sorted(p.name for p in learner.practice_dir.iterdir()) == [
        "attempts",
        "journal.jsonl",
        "journal.jsonl.lock",
    ]
