# ABOUTME: Unit tests for deriving attempt status, resume and progress from events.
# ABOUTME: Journal records are built by hand; attempt files are real files on disk.

import hashlib
from pathlib import Path
from typing import Any

import pytest

from practice.history import (
    AttemptError,
    attempt_code_path,
    build_history,
    find_attempt,
    latest_unfinished,
    summarize_problems,
    view_attempt,
)

HASH_A = "a" * 64


def sha(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()


def started(attempt_id: str, problem_id: str = "1") -> dict[str, Any]:
    return {
        "type": "attempt_started",
        "event_id": f"e-{attempt_id}",
        "at": "2026-10-28T10:00:00.000+00:00",
        "attempt_id": attempt_id,
        "platform": "leetcode",
        "problem_id": problem_id,
        "title": "Two Sum",
        "language": "python",
        "mode": "practice",
        "timed": False,
    }


def run_event(attempt_id: str, code: str, status: str) -> dict[str, Any]:
    return {
        "type": "test_run",
        "event_id": f"t-{attempt_id}-{code[:6]}-{status}",
        "at": "2026-10-28T10:05:00.000+00:00",
        "attempt_id": attempt_id,
        "status": status,
        "message": "m",
        "code_sha256": code,
        "suite_sha256": "s" * 64,
        "suite_version": "v1",
    }


def write_code(practice_dir: Path, attempt_id: str, text: str) -> None:
    path = attempt_code_path(practice_dir, "leetcode", "1", attempt_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(text.encode())


def test_attempt_with_no_runs_is_in_progress(tmp_path: Path) -> None:
    write_code(tmp_path, "a1", "x = 1\n")
    history = build_history([started("a1")])

    view = view_attempt(history.attempts[0], tmp_path)

    assert view.status == "in_progress"
    assert view.latest_run is None


def test_passing_run_on_current_code_is_passed(tmp_path: Path) -> None:
    write_code(tmp_path, "a1", "x = 1\n")
    history = build_history([started("a1"), run_event("a1", sha("x = 1\n"), "passed")])

    assert view_attempt(history.attempts[0], tmp_path).status == "passed"


def test_edit_after_a_pass_makes_the_pass_stale_but_keeps_evidence(
    tmp_path: Path,
) -> None:
    write_code(tmp_path, "a1", "x = 2\n")
    records = [started("a1"), run_event("a1", sha("x = 1\n"), "passed")]
    history = build_history(records)

    view = view_attempt(history.attempts[0], tmp_path)

    assert view.status == "stale"
    assert view.latest_pass is not None
    assert view.latest_pass["code_sha256"] == sha("x = 1\n")
    assert len(history.attempts[0].events) == 2  # Prior evidence stays in the log.


def test_reverting_to_the_passing_code_makes_it_current_again(tmp_path: Path) -> None:
    write_code(tmp_path, "a1", "x = 1\n")
    records = [
        started("a1"),
        run_event("a1", sha("x = 1\n"), "passed"),
        run_event("a1", sha("x = 2\n"), "failed"),
    ]

    view = view_attempt(build_history(records).attempts[0], tmp_path)

    assert view.status == "passed"


def test_failing_latest_run_on_current_code_is_not_a_pass(tmp_path: Path) -> None:
    write_code(tmp_path, "a1", "x = 1\n")
    records = [
        started("a1"),
        run_event("a1", sha("x = 1\n"), "passed"),
        run_event("a1", sha("x = 1\n"), "failed"),
    ]

    view = view_attempt(build_history(records).attempts[0], tmp_path)

    assert view.status == "in_progress"


def test_only_failures_never_pass(tmp_path: Path) -> None:
    write_code(tmp_path, "a1", "x = 2\n")
    records = [started("a1"), run_event("a1", HASH_A, "failed")]

    view = view_attempt(build_history(records).attempts[0], tmp_path)

    assert view.status == "in_progress"


def test_missing_code_file_cannot_be_current(tmp_path: Path) -> None:
    records = [started("a1"), run_event("a1", HASH_A, "passed")]

    view = view_attempt(build_history(records).attempts[0], tmp_path)

    assert view.current_sha256 is None
    assert view.status == "stale"


def test_latest_unfinished_prefers_most_recent_and_skips_finished() -> None:
    records = [
        started("a1"),
        started("a2"),
        {"type": "attempt_finished", "event_id": "f", "attempt_id": "a2", "at": "t"},
        started("a3", problem_id="2"),
    ]
    history = build_history(records)

    newest = latest_unfinished(history, None, None)
    assert newest is not None
    assert newest.attempt_id == "a3"
    same_problem = latest_unfinished(history, "leetcode", "1")
    assert same_problem is not None
    assert same_problem.attempt_id == "a1"
    assert latest_unfinished(history, "leetcode", "9") is None


def test_events_for_unknown_attempts_become_notices() -> None:
    history = build_history([run_event("ghost", HASH_A, "passed")])

    assert history.attempts == []
    assert len(history.notices) == 1
    assert "ghost" in history.notices[0]


def test_unknown_event_types_are_ignored_for_forward_compatibility() -> None:
    odd = {"type": "future_thing", "event_id": "z", "at": "t", "attempt_id": "a1"}

    history = build_history([started("a1"), odd])

    assert history.notices == []
    assert len(history.attempts) == 1


def test_find_attempt_accepts_exact_ids_and_unique_prefixes() -> None:
    history = build_history([started("20261028-aaaa"), started("20261028-bbbb")])

    assert find_attempt(history, "20261028-aaaa").attempt_id == "20261028-aaaa"
    assert find_attempt(history, "20261028-b").attempt_id == "20261028-bbbb"
    with pytest.raises(AttemptError, match="ambiguous"):
        find_attempt(history, "20261028")
    with pytest.raises(AttemptError, match="no attempt"):
        find_attempt(history, "zzz")


def test_problem_summary_ranks_passed_over_stale_over_in_progress(
    tmp_path: Path,
) -> None:
    write_code(tmp_path, "a1", "x = 2\n")
    write_code(tmp_path, "a2", "y = 1\n")
    records = [
        started("a1"),
        run_event("a1", sha("x = 1\n"), "passed"),
        started("a2"),
        run_event("a2", sha("y = 1\n"), "passed"),
    ]
    history = build_history(records)
    views = [view_attempt(a, tmp_path) for a in history.attempts]

    summaries = summarize_problems(views)

    assert len(summaries) == 1
    assert summaries[0].status == "passed"
    assert [v.attempt.attempt_id for v in summaries[0].attempts] == ["a1", "a2"]


def test_platform_verdict_is_separate_from_local_status(tmp_path: Path) -> None:
    write_code(tmp_path, "a1", "x = 1\n")
    records = [
        started("a1"),
        {
            "type": "platform_verdict",
            "event_id": "v1",
            "at": "t",
            "attempt_id": "a1",
            "status": "accepted",
            "source": "LeetCode submissions page",
            "date": "2026-10-28",
        },
    ]
    history = build_history(records)
    view = view_attempt(history.attempts[0], tmp_path)
    summary = summarize_problems([view])[0]

    assert view.status == "in_progress"  # Acceptance does not invent a local pass.
    assert summary.status == "in_progress"
    assert summary.verdict is not None
    assert summary.verdict["status"] == "accepted"


def test_no_verdict_means_none_is_recorded(tmp_path: Path) -> None:
    write_code(tmp_path, "a1", "x = 1\n")
    history = build_history([started("a1")])

    summary = summarize_problems([view_attempt(history.attempts[0], tmp_path)])[0]

    assert summary.verdict is None
