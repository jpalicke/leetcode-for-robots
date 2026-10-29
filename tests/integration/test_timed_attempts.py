# ABOUTME: Integration tests for timed attempts against real journal files and the CLI.
# ABOUTME: Covers reset after a timed attempt and that timing never moves any outcome.

import hashlib
from datetime import date
from pathlib import Path
from typing import Any

import pytest

from practice.attempts import (
    finish_attempt,
    record_explanation,
    start_attempt,
)
from practice.catalog import DEFAULT_CATALOG_PATH, load_catalog
from practice.curriculum import DEFAULT_CURRICULUM_PATH, load_curriculum
from practice.history import (
    AttemptError,
    attempt_code_path,
    find_attempt,
    journal_for,
    load_history,
    view_attempt,
)
from practice.menu import MenuEnvironment, Screen, build_menu, choose
from practice.package import load_package
from practice.paths import REPO_ROOT
from practice.recommendations import Recommendation, build_recommendation
from practice.reviews import ReviewSchedule, load_schedule
from practice.rubric import ExplanationScores
from practice.tutor_commands import briefing

PACKAGE_DIR = REPO_ROOT / "problems" / "leetcode-1"
DAY = "2026-11-02"


def begin(practice_dir: Path, *, timed: bool = False, limit: int | None = None) -> str:
    return start_attempt(
        practice_dir,
        load_catalog(DEFAULT_CATALOG_PATH),
        load_package(PACKAGE_DIR),
        "leetcode",
        "1",
        language="python",
        mode="practice",
        timed=timed,
        limit_minutes=limit,
    ).attempt_id


def started_events(practice_dir: Path) -> list[dict[str, Any]]:
    return [
        r
        for r in journal_for(practice_dir).read().records
        if r["type"] == "attempt_started"
    ]


def test_a_timed_start_records_the_timer_and_the_limit(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("PRACTICE_NOW", f"{DAY}T09:00:00Z")

    begin(tmp_path, timed=True, limit=45)

    (event,) = started_events(tmp_path)
    assert event["timed"] is True
    assert event["limit_minutes"] == 45
    assert event["at"] == f"{DAY}T09:00:00.000+00:00"


def test_a_timed_start_without_a_limit_records_no_limit(tmp_path: Path) -> None:
    begin(tmp_path, timed=True)

    (event,) = started_events(tmp_path)
    assert event["timed"] is True
    assert "limit_minutes" not in event


def test_a_limit_without_timing_is_refused_and_nothing_is_written(
    tmp_path: Path,
) -> None:
    with pytest.raises(AttemptError, match="--timed"):
        begin(tmp_path, timed=False, limit=30)

    assert not (tmp_path / "journal.jsonl").exists()
    assert not (tmp_path / "attempts").exists()


def test_the_attempt_after_a_timed_one_starts_untimed_in_saved_history(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("PRACTICE_NOW", f"{DAY}T09:00:00Z")
    timed_id = begin(tmp_path, timed=True, limit=30)
    monkeypatch.setenv("PRACTICE_NOW", f"{DAY}T09:20:00Z")
    finish_attempt(tmp_path, find_attempt(load_history(tmp_path), timed_id))
    monkeypatch.setenv("PRACTICE_NOW", f"{DAY}T10:00:00Z")

    next_id = begin(tmp_path)  # A fresh start; nothing is asked of the earlier one.

    saved = load_history(tmp_path)  # Read back from the file on disk.
    assert [(a.attempt_id, a.timed) for a in saved.attempts] == [
        (timed_id, True),
        (next_id, False),
    ]
    assert saved.attempts[0].limit_minutes == 30
    assert saved.attempts[1].limit_minutes is None
    assert "limit_minutes" not in started_events(tmp_path)[1]


def test_a_timed_attempt_does_not_make_the_next_session_briefing_timed(
    tmp_path: Path,
) -> None:
    timed_id = begin(tmp_path, timed=True)
    assert "Timing: timed" in "\n".join(briefing(load_history(tmp_path), tmp_path))
    finish_attempt(tmp_path, find_attempt(load_history(tmp_path), timed_id))

    after_finish = "\n".join(briefing(load_history(tmp_path), tmp_path))
    begin(tmp_path)
    next_attempt = "\n".join(briefing(load_history(tmp_path), tmp_path))

    assert "Timing: untimed" in after_finish
    assert "Timing: untimed" in next_attempt
    assert "Timing: timed" not in next_attempt


def test_the_menu_start_after_a_timed_attempt_is_untimed(
    menu_env: MenuEnvironment,
) -> None:
    problem = Screen("problem", platform="leetcode", problem_id="1")
    keys = [item.key for item in build_menu(menu_env, problem).items]
    timed = choose(menu_env, problem, keys.index("start-timed") + 1)
    assert timed.code == 0, timed.stderr
    finish_attempt(
        menu_env.practice_dir,
        find_attempt(load_history(menu_env.practice_dir), timed.next_screen.attempt_id),
    )

    plain = choose(menu_env, problem, keys.index("start") + 1)

    assert plain.code == 0, plain.stderr
    flags = [a.timed for a in load_history(menu_env.practice_dir).attempts]
    assert flags == [True, False]


# Timing is evidence only: the same journal with and without it gives the same
# explanation scores, completion, review ladder and recommendation.


def write_world(
    practice_dir: Path,
    monkeypatch: pytest.MonkeyPatch,
    *,
    timed: bool,
    pass_hour: int,
) -> None:
    """An ordinary attempt that passes, then a passing review the next day.

    Timed worlds carry a 5 minute limit that the slow pass badly misses.
    """
    journal = journal_for(practice_dir)
    source = "def f():\n    return 1\n"
    digest = hashlib.sha256(source.encode()).hexdigest()
    for attempt_id, day, review in (
        ("a1", "2026-11-02", False),
        ("a2", "2026-11-03", True),
    ):
        monkeypatch.setenv("PRACTICE_NOW", f"{day}T09:00:00Z")
        path = attempt_code_path(practice_dir, "leetcode", "1", attempt_id)
        path.parent.mkdir(parents=True)
        path.write_text(source, encoding="utf-8")
        fields: dict[str, Any] = {
            "attempt_id": attempt_id,
            "platform": "leetcode",
            "problem_id": "1",
            "title": "Two Sum",
            "language": "python",
            "mode": "practice",
            "timed": timed and not review,
        }
        if timed and not review:
            fields["limit_minutes"] = 5
        if review:
            fields["review"] = True
        journal.append("attempt_started", **fields)
        monkeypatch.setenv("PRACTICE_NOW", f"{day}T{pass_hour:02d}:00:00Z")
        journal.append(
            "test_run",
            attempt_id=attempt_id,
            status="passed",
            message="m",
            code_sha256=digest,
        )
        journal.append("attempt_finished", attempt_id=attempt_id)
    monkeypatch.setenv("PRACTICE_NOW", "2026-11-03T22:00:00Z")
    attempt = find_attempt(load_history(practice_dir), "a1")
    record_explanation(
        practice_dir,
        attempt,
        ExplanationScores(approach=4, correctness=3, time=2, space=None),
        evidence="said it",
        feedback="fine",
        coaching=None,
    )


def snapshot(practice_dir: Path) -> tuple[Any, ...]:
    history = load_history(practice_dir)
    views = [view_attempt(a, practice_dir) for a in history.attempts]
    schedule: ReviewSchedule = load_schedule(practice_dir)
    catalog = load_catalog(DEFAULT_CATALOG_PATH)
    recommendation: Recommendation = build_recommendation(
        practice_dir,
        catalog,
        load_curriculum(DEFAULT_CURRICULUM_PATH, catalog),
        lambda platform, problem_id: problem_id in {"1", "217"},
        date(2026, 11, 4),
    )
    return (
        [(v.status, v.attempt.finished_at is not None) for v in views],
        [
            [(e.scores, e.is_current, e.code_passed) for e in v.explanations]
            for v in views
        ],
        schedule.items,
        recommendation,
    )


def test_timing_changes_no_score_completion_ladder_or_recommendation(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    untimed = tmp_path / "untimed"
    quick = tmp_path / "quick"
    slow = tmp_path / "slow"
    write_world(untimed, monkeypatch, timed=False, pass_hour=9)
    write_world(quick, monkeypatch, timed=True, pass_hour=9)
    write_world(
        slow, monkeypatch, timed=True, pass_hour=20
    )  # Hours over a 5 min limit.

    baseline = snapshot(untimed)
    monkeypatch.setenv("PRACTICE_NOW", "2026-11-04T09:00:00Z")

    assert snapshot(quick) == baseline
    assert snapshot(slow) == baseline
    assert baseline[2], "the review ladder must hold an item for this to mean anything"
