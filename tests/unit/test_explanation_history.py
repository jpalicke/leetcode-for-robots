# ABOUTME: Unit tests for deriving explanation assessment views from journal events.
# ABOUTME: Revision numbers come from journal order; staleness comes from the code hash.

import hashlib
from pathlib import Path
from typing import Any

from practice.history import attempt_code_path, build_history, view_attempt


def sha(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()


def base(kind: str, event_id: str, **fields: Any) -> dict[str, Any]:
    return {
        "type": kind,
        "event_id": event_id,
        "at": "2026-10-28T10:00:00.000+00:00",
        "attempt_id": "a1",
        **fields,
    }


def started() -> dict[str, Any]:
    return base(
        "attempt_started",
        "e0",
        platform="leetcode",
        problem_id="1",
        title="Two Sum",
        language="python",
        mode="practice",
        timed=False,
    )


def run(code: str, status: str = "passed") -> dict[str, Any]:
    return base(
        "test_run",
        f"r-{code[:4]}-{status}",
        status=status,
        message="m",
        code_sha256=sha(code),
        suite_sha256="s" * 64,
        suite_version="v1",
    )


def assessment(event_id: str, code: str, **scores: Any) -> dict[str, Any]:
    fields: dict[str, Any] = {
        "approach": None,
        "correctness": None,
        "time_complexity": None,
        "space_complexity": None,
        "evidence": "said it",
        "feedback": "good",
        "code_sha256": sha(code),
    }
    fields.update(scores)
    return base("explanation_assessment", event_id, **fields)


def write_code(practice_dir: Path, text: str) -> None:
    path = attempt_code_path(practice_dir, "leetcode", "1", "a1")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(text.encode())


def test_no_assessment_means_no_explanations(tmp_path: Path) -> None:
    write_code(tmp_path, "x = 1\n")
    view = view_attempt(build_history([started()]).attempts[0], tmp_path)

    assert view.explanations == []
    assert view.latest_explanation is None


def test_first_is_initial_and_later_ones_are_numbered_revisions(
    tmp_path: Path,
) -> None:
    write_code(tmp_path, "x = 1\n")
    records = [
        started(),
        assessment("x1", "x = 1\n", approach=2),
        assessment("x2", "x = 1\n", approach=3),
        assessment("x3", "x = 1\n", approach=4),
    ]

    view = view_attempt(build_history(records).attempts[0], tmp_path)

    assert [e.sequence for e in view.explanations] == [1, 2, 3]
    assert [e.label for e in view.explanations] == [
        "initial",
        "revision 1",
        "revision 2",
    ]
    assert view.latest_explanation is view.explanations[-1]
    assert [e.scores.approach for e in view.explanations] == [2, 3, 4]


def test_assessment_is_current_for_matching_code_and_stale_after_an_edit(
    tmp_path: Path,
) -> None:
    write_code(tmp_path, "x = 1\n")
    history = build_history([started(), assessment("x1", "x = 1\n", approach=4)])

    assert view_attempt(history.attempts[0], tmp_path).explanations[0].is_current

    write_code(tmp_path, "x = 2\n")
    edited = view_attempt(history.attempts[0], tmp_path)

    assert edited.explanations[0].is_current is False
    assert edited.explanations[0].scores.approach == 4  # Evidence stays.


def test_assessment_is_labelled_when_the_assessed_code_never_passed(
    tmp_path: Path,
) -> None:
    write_code(tmp_path, "x = 1\n")
    without = build_history([started(), assessment("x1", "x = 1\n", approach=4)])
    failed = build_history(
        [started(), run("x = 1\n", "failed"), assessment("x1", "x = 1\n", approach=4)]
    )
    passed = build_history(
        [started(), run("x = 1\n"), assessment("x1", "x = 1\n", approach=4)]
    )

    assert not view_attempt(without.attempts[0], tmp_path).explanations[0].code_passed
    assert not view_attempt(failed.attempts[0], tmp_path).explanations[0].code_passed
    assert view_attempt(passed.attempts[0], tmp_path).explanations[0].code_passed


def test_assessment_never_changes_the_local_status(tmp_path: Path) -> None:
    write_code(tmp_path, "x = 1\n")
    with_it = build_history(
        [started(), run("x = 1\n"), assessment("x1", "x = 1\n", approach=0)]
    )
    without_it = build_history([started(), run("x = 1\n")])

    assert view_attempt(with_it.attempts[0], tmp_path).status == "passed"
    assert view_attempt(without_it.attempts[0], tmp_path).status == "passed"
    failing = build_history([started(), assessment("x1", "x = 1\n", approach=4)])
    assert view_attempt(failing.attempts[0], tmp_path).status == "in_progress"


def test_a_malformed_assessment_is_reported_and_skipped() -> None:
    bad = assessment("x1", "x = 1\n", approach=9)

    history = build_history([started(), bad])

    assert history.attempts[0].events == [started()]
    assert any("x1" in notice and "approach" in notice for notice in history.notices)
