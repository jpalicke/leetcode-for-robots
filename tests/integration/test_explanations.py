# ABOUTME: Integration tests for recording explanation assessments in the real journal.
# ABOUTME: Covers persistence, revisions, staleness, ungraded versus zero, validation.

import json
import shutil
from collections.abc import Callable
from pathlib import Path

import pytest

from practice.attempts import (
    record_assistance,
    record_explanation,
    run_attempt_tests,
    start_attempt,
)
from practice.catalog import DEFAULT_CATALOG_PATH, Catalog, load_catalog
from practice.history import (
    Attempt,
    AttemptError,
    attempt_code_path,
    load_history,
    view_attempt,
)
from practice.package import ExercisePackage, load_package
from practice.rubric import ExplanationScores

Solution = Callable[[str], Path]
FULL = ExplanationScores(approach=4, correctness=4, time=2, space=1)


@pytest.fixture(scope="module")
def catalog() -> Catalog:
    return load_catalog(DEFAULT_CATALOG_PATH)


@pytest.fixture
def practice_dir(tmp_path: Path) -> Path:
    return tmp_path / "learner"


@pytest.fixture
def package(leetcode_two_sum_package: Path) -> ExercisePackage:
    return load_package(leetcode_two_sum_package)


def begin(
    practice_dir: Path,
    catalog: Catalog,
    package: ExercisePackage,
    *,
    timed: bool = False,
) -> Attempt:
    started = start_attempt(
        practice_dir,
        catalog,
        package,
        "leetcode",
        "1",
        language="python",
        mode="practice",
        timed=timed,
    )
    return next(
        a
        for a in load_history(practice_dir).attempts
        if a.attempt_id == started.attempt_id
    )


def solve(
    practice_dir: Path,
    attempt: Attempt,
    package: ExercisePackage,
    two_sum_solution: Solution,
    name: str,
) -> None:
    code = attempt_code_path(practice_dir, "leetcode", "1", attempt.attempt_id)
    shutil.copyfile(two_sum_solution(name), code)
    run_attempt_tests(practice_dir, attempt, package, timeout=60)


def reload(practice_dir: Path, attempt: Attempt) -> Attempt:
    return next(
        a
        for a in load_history(practice_dir).attempts
        if a.attempt_id == attempt.attempt_id
    )


def test_assessment_is_appended_to_the_journal_with_evidence_and_code_hash(
    practice_dir: Path,
    catalog: Catalog,
    package: ExercisePackage,
    two_sum_solution: Solution,
) -> None:
    attempt = begin(practice_dir, catalog, package)
    solve(practice_dir, attempt, package, two_sum_solution, "correct_hash_map")

    record_explanation(
        practice_dir,
        attempt,
        FULL,
        evidence="Stored complements in a dict, one pass.",
        feedback="Clear and correct.",
        coaching=None,
    )

    lines = (practice_dir / "journal.jsonl").read_text(encoding="utf-8").splitlines()
    event = json.loads(lines[-1])
    view = view_attempt(reload(practice_dir, attempt), practice_dir)
    assert event["type"] == "explanation_assessment"
    assert event["attempt_id"] == attempt.attempt_id
    assert event["code_sha256"] == view.current_sha256
    assert (event["approach"], event["correctness"]) == (4, 4)
    assert (event["time_complexity"], event["space_complexity"]) == (2, 1)
    assert event["evidence"] == "Stored complements in a dict, one pass."
    assert event["feedback"] == "Clear and correct."
    assert "coaching" not in event


def test_initial_and_revised_assessments_are_both_kept_in_order(
    practice_dir: Path,
    catalog: Catalog,
    package: ExercisePackage,
    two_sum_solution: Solution,
) -> None:
    attempt = begin(practice_dir, catalog, package)
    solve(practice_dir, attempt, package, two_sum_solution, "correct_hash_map")
    first = ExplanationScores(approach=2, correctness=2, time=1, space=None)

    record_explanation(practice_dir, attempt, first, "vague", "needs why", None)
    before = (practice_dir / "journal.jsonl").read_bytes()
    record_explanation(practice_dir, attempt, FULL, "clear now", "great", None)

    after = (practice_dir / "journal.jsonl").read_bytes()
    assert after.startswith(before)  # Append only; the first line is untouched.
    view = view_attempt(reload(practice_dir, attempt), practice_dir)
    assert [e.label for e in view.explanations] == ["initial", "revision 1"]
    assert [e.scores.core_total for e in view.explanations] == [5, 10]
    assert view.explanations[0].evidence == "vague"
    assert view.latest_explanation is view.explanations[1]


def test_assessment_goes_stale_after_an_edit_but_stays_in_history(
    practice_dir: Path,
    catalog: Catalog,
    package: ExercisePackage,
    two_sum_solution: Solution,
) -> None:
    attempt = begin(practice_dir, catalog, package)
    solve(practice_dir, attempt, package, two_sum_solution, "correct_hash_map")
    record_explanation(practice_dir, attempt, FULL, "e", "f", None)
    code = attempt_code_path(practice_dir, "leetcode", "1", attempt.attempt_id)
    original = code.read_bytes()

    code.write_bytes(original + b"\n# tweak\n")
    edited = view_attempt(reload(practice_dir, attempt), practice_dir)
    code.write_bytes(original)
    reverted = view_attempt(reload(practice_dir, attempt), practice_dir)

    assert edited.explanations[0].is_current is False
    assert reverted.explanations[0].is_current is True


def test_ungraded_components_are_stored_as_null_and_zero_stays_zero(
    practice_dir: Path,
    catalog: Catalog,
    package: ExercisePackage,
    two_sum_solution: Solution,
) -> None:
    attempt = begin(practice_dir, catalog, package)
    solve(practice_dir, attempt, package, two_sum_solution, "correct_hash_map")
    partial = ExplanationScores(approach=0, correctness=None, time=None, space=0)

    record_explanation(practice_dir, attempt, partial, "e", "f", None)

    event = json.loads(
        (practice_dir / "journal.jsonl").read_text(encoding="utf-8").splitlines()[-1]
    )
    assert event["approach"] == 0
    assert event["correctness"] is None
    assert event["time_complexity"] is None
    assert event["space_complexity"] == 0


def test_an_accurate_explanation_of_slower_code_earns_full_core_credit(
    practice_dir: Path,
    catalog: Catalog,
    package: ExercisePackage,
    two_sum_solution: Solution,
) -> None:
    attempt = begin(practice_dir, catalog, package, timed=True)
    record_assistance(practice_dir, attempt, "hint", 2, "nudged at repeated work")
    attempt = reload(practice_dir, attempt)
    solve(practice_dir, attempt, package, two_sum_solution, "correct_brute_force")
    full_core = ExplanationScores(approach=4, correctness=4, time=2, space=None)

    record_explanation(
        practice_dir,
        attempt,
        full_core,
        "Checked every pair; O(n^2) time.",
        "Accurate.",
        coaching="Ask what work repeats across the inner loops.",
    )

    view = view_attempt(reload(practice_dir, attempt), practice_dir)
    latest = view.latest_explanation
    assert latest is not None
    assert latest.scores.core_total == 10  # Hints and timing subtract nothing.
    assert latest.scores.bonus is None
    assert latest.coaching == "Ask what work repeats across the inner loops."
    assert view.status == "passed"


def test_recording_an_assessment_does_not_change_completion(
    practice_dir: Path,
    catalog: Catalog,
    package: ExercisePackage,
    two_sum_solution: Solution,
) -> None:
    attempt = begin(practice_dir, catalog, package)
    solve(practice_dir, attempt, package, two_sum_solution, "correct_hash_map")
    zero = ExplanationScores(approach=0, correctness=0, time=0, space=0)

    record_explanation(practice_dir, attempt, zero, "silent", "try again", None)

    assert view_attempt(reload(practice_dir, attempt), practice_dir).status == "passed"


def test_assessing_an_attempt_with_no_passing_run_is_allowed_and_labelled(
    practice_dir: Path, catalog: Catalog, package: ExercisePackage
) -> None:
    attempt = begin(practice_dir, catalog, package)

    record_explanation(practice_dir, attempt, FULL, "e", "f", None)

    view = view_attempt(reload(practice_dir, attempt), practice_dir)
    assert view.status == "in_progress"
    assert view.explanations[0].code_passed is False


@pytest.mark.parametrize(
    "scores",
    [
        ExplanationScores(5, None, None, None),
        ExplanationScores(None, 5, None, None),
        ExplanationScores(None, None, 3, None),
        ExplanationScores(None, None, None, 2),
        ExplanationScores(-1, None, None, None),
    ],
)
def test_out_of_range_scores_are_rejected_and_nothing_is_written(
    practice_dir: Path,
    catalog: Catalog,
    package: ExercisePackage,
    scores: ExplanationScores,
) -> None:
    attempt = begin(practice_dir, catalog, package)
    before = (practice_dir / "journal.jsonl").read_bytes()

    with pytest.raises(AttemptError, match="0 to"):
        record_explanation(practice_dir, attempt, scores, "e", "f", None)

    assert (practice_dir / "journal.jsonl").read_bytes() == before


@pytest.mark.parametrize(("evidence", "feedback"), [("", "f"), ("e", "  ")])
def test_evidence_and_feedback_are_required(
    practice_dir: Path,
    catalog: Catalog,
    package: ExercisePackage,
    evidence: str,
    feedback: str,
) -> None:
    attempt = begin(practice_dir, catalog, package)

    with pytest.raises(AttemptError, match="evidence and feedback"):
        record_explanation(practice_dir, attempt, FULL, evidence, feedback, None)


def test_an_explicitly_ungraded_assessment_is_allowed(
    practice_dir: Path, catalog: Catalog, package: ExercisePackage
) -> None:
    attempt = begin(practice_dir, catalog, package)
    nothing = ExplanationScores(None, None, None, None)

    record_explanation(practice_dir, attempt, nothing, "deferred", "later", None)

    view = view_attempt(reload(practice_dir, attempt), practice_dir)
    assert view.explanations[0].scores.is_ungraded
