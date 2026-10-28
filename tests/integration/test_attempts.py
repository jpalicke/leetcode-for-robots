# ABOUTME: Integration tests for attempt operations on real files and the real runner.
# ABOUTME: Covers starters, preserved code, test evidence, staleness and validation.

import hashlib
import json
import shutil
from collections.abc import Callable
from pathlib import Path

import pytest

from practice.attempts import (
    finish_attempt,
    record_assistance,
    record_verdict,
    run_attempt_tests,
    start_attempt,
)
from practice.catalog import DEFAULT_CATALOG_PATH, Catalog, load_catalog
from practice.history import (
    AttemptError,
    attempt_code_path,
    find_attempt,
    load_history,
    view_attempt,
)
from practice.package import load_package

Solution = Callable[[str], Path]


@pytest.fixture(scope="module")
def catalog() -> Catalog:
    return load_catalog(DEFAULT_CATALOG_PATH)


@pytest.fixture
def practice_dir(tmp_path: Path) -> Path:
    return tmp_path / "learner"


def begin(
    practice_dir: Path,
    catalog: Catalog,
    package_dir: Path,
    *,
    mode: str = "practice",
    timed: bool = False,
) -> str:
    package = load_package(package_dir)
    started = start_attempt(
        practice_dir,
        catalog,
        package,
        "leetcode",
        "1",
        language="python",
        mode=mode,
        timed=timed,
    )
    return started.attempt_id


def test_start_without_a_starter_writes_a_blank_stub_from_the_signature(
    practice_dir: Path, catalog: Catalog, leetcode_two_sum_package: Path
) -> None:
    attempt_id = begin(practice_dir, catalog, leetcode_two_sum_package)

    code = attempt_code_path(practice_dir, "leetcode", "1", attempt_id)
    assert code.read_text(encoding="utf-8") == "def two_sum(nums, target):\n    pass\n"
    assert code.parent.name == attempt_id
    assert code.parent.parent.name == "leetcode-1"


def test_start_uses_the_package_starter_when_one_exists(
    practice_dir: Path, catalog: Catalog, leetcode_two_sum_package: Path
) -> None:
    starter = "def two_sum(nums: list[int], target: int) -> list[int]:\n    ...\n"
    (leetcode_two_sum_package / "starter.py").write_bytes(starter.encode())

    attempt_id = begin(practice_dir, catalog, leetcode_two_sum_package)

    code = attempt_code_path(practice_dir, "leetcode", "1", attempt_id)
    assert code.read_text(encoding="utf-8") == starter
    started = load_history(practice_dir).attempts[0].events[0]
    assert started["starter_source"] == "package starter"
    assert started["starter_sha256"] == hashlib.sha256(starter.encode()).hexdigest()


def test_start_records_identity_language_mode_and_timing_opt_in(
    practice_dir: Path, catalog: Catalog, leetcode_two_sum_package: Path
) -> None:
    attempt_id = begin(
        practice_dir, catalog, leetcode_two_sum_package, mode="study", timed=True
    )

    event = load_history(practice_dir).attempts[0].events[0]
    assert event["type"] == "attempt_started"
    assert event["attempt_id"] == attempt_id
    assert (event["platform"], event["problem_id"]) == ("leetcode", "1")
    assert event["title"] == "Two Sum"
    assert (event["language"], event["mode"], event["timed"]) == (
        "python",
        "study",
        True,
    )


def test_timing_is_never_carried_forward_from_a_prior_attempt(
    practice_dir: Path, catalog: Catalog, leetcode_two_sum_package: Path
) -> None:
    begin(practice_dir, catalog, leetcode_two_sum_package, timed=True)
    begin(practice_dir, catalog, leetcode_two_sum_package)

    attempts = load_history(practice_dir).attempts

    assert [a.timed for a in attempts] == [True, False]


def test_a_new_attempt_never_touches_earlier_code(
    practice_dir: Path, catalog: Catalog, leetcode_two_sum_package: Path
) -> None:
    first = begin(practice_dir, catalog, leetcode_two_sum_package)
    first_code = attempt_code_path(practice_dir, "leetcode", "1", first)
    first_code.write_text("def two_sum(nums, target):\n    return [0, 1]\n")
    before = first_code.read_bytes()

    second = begin(practice_dir, catalog, leetcode_two_sum_package)

    second_code = attempt_code_path(practice_dir, "leetcode", "1", second)
    assert second != first
    assert first_code.read_bytes() == before
    assert second_code.read_text(encoding="utf-8") == (
        "def two_sum(nums, target):\n    pass\n"
    )


@pytest.mark.parametrize(
    ("platform", "problem_id", "fragment"),
    [
        ("leetcode", "999999", "not in the leetcode catalog"),
        ("leetcode", "two-sum", "not in the leetcode catalog"),
        ("hackerrank", "1", "no catalog"),
    ],
)
def test_unknown_problems_are_rejected_before_anything_is_written(
    practice_dir: Path,
    catalog: Catalog,
    leetcode_two_sum_package: Path,
    platform: str,
    problem_id: str,
    fragment: str,
) -> None:
    package = load_package(leetcode_two_sum_package)

    with pytest.raises(AttemptError, match=fragment):
        start_attempt(
            practice_dir,
            catalog,
            package,
            platform,
            problem_id,
            language="python",
            mode="practice",
            timed=False,
        )

    assert not practice_dir.exists()


def test_package_for_a_different_problem_is_rejected(
    practice_dir: Path, catalog: Catalog, two_sum_package: Path
) -> None:
    package = load_package(two_sum_package)  # Declares platform "fixture".

    with pytest.raises(AttemptError, match="describes fixture"):
        start_attempt(
            practice_dir,
            catalog,
            package,
            "leetcode",
            "1",
            language="python",
            mode="practice",
            timed=False,
        )

    assert not practice_dir.exists()


@pytest.mark.parametrize(
    ("language", "mode", "fragment"),
    [("rust", "practice", "language"), ("python", "relaxed", "mode")],
)
def test_unsupported_language_or_mode_is_rejected(
    practice_dir: Path,
    catalog: Catalog,
    leetcode_two_sum_package: Path,
    language: str,
    mode: str,
    fragment: str,
) -> None:
    package = load_package(leetcode_two_sum_package)

    with pytest.raises(AttemptError, match=fragment):
        start_attempt(
            practice_dir,
            catalog,
            package,
            "leetcode",
            "1",
            language=language,
            mode=mode,
            timed=False,
        )

    assert not practice_dir.exists()


def test_test_run_records_runner_evidence(
    practice_dir: Path,
    catalog: Catalog,
    leetcode_two_sum_package: Path,
    two_sum_solution: Solution,
) -> None:
    attempt_id = begin(practice_dir, catalog, leetcode_two_sum_package)
    code = attempt_code_path(practice_dir, "leetcode", "1", attempt_id)
    shutil.copyfile(two_sum_solution("correct_hash_map"), code)
    package = load_package(leetcode_two_sum_package)
    attempt = find_attempt(load_history(practice_dir), attempt_id)

    result = run_attempt_tests(practice_dir, attempt, package, timeout=20.0)

    assert result.status == "passed"
    event = load_history(practice_dir).attempts[0].events[-1]
    assert event["type"] == "test_run"
    assert event["status"] == "passed"
    assert event["code_sha256"] == hashlib.sha256(code.read_bytes()).hexdigest()
    assert event["code_sha256"] == result.code_sha256
    assert event["suite_sha256"] == package.suite_sha256
    assert event["suite_version"] == "fixture-1"
    view = view_attempt(
        find_attempt(load_history(practice_dir), attempt_id), practice_dir
    )
    assert view.status == "passed"


def test_unwritten_starter_is_recorded_as_a_stub_and_never_a_pass(
    practice_dir: Path, catalog: Catalog, leetcode_two_sum_package: Path
) -> None:
    attempt_id = begin(practice_dir, catalog, leetcode_two_sum_package)
    package = load_package(leetcode_two_sum_package)
    attempt = find_attempt(load_history(practice_dir), attempt_id)

    result = run_attempt_tests(practice_dir, attempt, package, timeout=20.0)

    assert result.status == "stub"
    history = load_history(practice_dir)
    assert view_attempt(history.attempts[0], practice_dir).status == "in_progress"


def test_editing_after_a_pass_marks_it_stale_and_retesting_restores_it(
    practice_dir: Path,
    catalog: Catalog,
    leetcode_two_sum_package: Path,
    two_sum_solution: Solution,
) -> None:
    attempt_id = begin(practice_dir, catalog, leetcode_two_sum_package)
    code = attempt_code_path(practice_dir, "leetcode", "1", attempt_id)
    shutil.copyfile(two_sum_solution("correct_hash_map"), code)
    package = load_package(leetcode_two_sum_package)

    def test_now() -> str:
        attempt = find_attempt(load_history(practice_dir), attempt_id)
        return run_attempt_tests(practice_dir, attempt, package, timeout=20.0).status

    def status_now() -> str:
        attempt = find_attempt(load_history(practice_dir), attempt_id)
        return view_attempt(attempt, practice_dir).status

    assert test_now() == "passed"
    assert status_now() == "passed"

    code.write_text(code.read_text(encoding="utf-8") + "\n# edited\n", encoding="utf-8")
    assert status_now() == "stale"
    events = load_history(practice_dir).attempts[0].events
    assert [e["type"] for e in events] == ["attempt_started", "test_run"]

    assert test_now() == "passed"
    assert status_now() == "passed"
    assert len(load_history(practice_dir).attempts[0].events) == 3


def test_changed_suite_is_visible_in_the_recorded_evidence(
    practice_dir: Path,
    catalog: Catalog,
    leetcode_two_sum_package: Path,
    two_sum_solution: Solution,
) -> None:
    attempt_id = begin(practice_dir, catalog, leetcode_two_sum_package)
    code = attempt_code_path(practice_dir, "leetcode", "1", attempt_id)
    shutil.copyfile(two_sum_solution("correct_hash_map"), code)
    attempt = find_attempt(load_history(practice_dir), attempt_id)
    run_attempt_tests(practice_dir, attempt, load_package(leetcode_two_sum_package), 20)
    suite_path = leetcode_two_sum_package / "tests.json"
    suite = json.loads(suite_path.read_text(encoding="utf-8"))
    suite["version"] = "fixture-2"
    suite_path.write_text(json.dumps(suite), encoding="utf-8")

    run_attempt_tests(practice_dir, attempt, load_package(leetcode_two_sum_package), 20)

    runs = [e for e in load_history(practice_dir).attempts[0].events if "status" in e]
    assert [r["suite_version"] for r in runs] == ["fixture-1", "fixture-2"]
    assert runs[0]["suite_sha256"] != runs[1]["suite_sha256"]


def test_test_run_against_the_wrong_package_is_rejected(
    practice_dir: Path,
    catalog: Catalog,
    leetcode_two_sum_package: Path,
    two_sum_package: Path,
) -> None:
    attempt_id = begin(practice_dir, catalog, leetcode_two_sum_package)
    attempt = find_attempt(load_history(practice_dir), attempt_id)

    with pytest.raises(AttemptError, match="describes fixture"):
        run_attempt_tests(practice_dir, attempt, load_package(two_sum_package), 5)

    assert len(load_history(practice_dir).attempts[0].events) == 1


def test_missing_attempt_file_is_an_error_not_a_recorded_run(
    practice_dir: Path, catalog: Catalog, leetcode_two_sum_package: Path
) -> None:
    attempt_id = begin(practice_dir, catalog, leetcode_two_sum_package)
    attempt_code_path(practice_dir, "leetcode", "1", attempt_id).unlink()
    attempt = find_attempt(load_history(practice_dir), attempt_id)

    with pytest.raises(AttemptError, match="cannot read"):
        run_attempt_tests(
            practice_dir, attempt, load_package(leetcode_two_sum_package), 5
        )

    assert len(load_history(practice_dir).attempts[0].events) == 1


def test_assistance_events_are_validated_and_recorded(
    practice_dir: Path, catalog: Catalog, leetcode_two_sum_package: Path
) -> None:
    attempt_id = begin(practice_dir, catalog, leetcode_two_sum_package)
    attempt = find_attempt(load_history(practice_dir), attempt_id)

    record_assistance(practice_dir, attempt, "hint", 2, "suggested a lookup table")
    record_assistance(practice_dir, attempt, "reveal", None, None)

    events = load_history(practice_dir).attempts[0].events[1:]
    assert [(e["type"], e["kind"], e["level"]) for e in events] == [
        ("assistance", "hint", 2),
        ("assistance", "reveal", None),
    ]
    assert events[0]["summary"] == "suggested a lookup table"


@pytest.mark.parametrize(
    ("kind", "level", "fragment"),
    [
        ("hint", None, "level"),
        ("hint", 4, "level"),
        ("hint", -1, "level"),
        ("reveal", 1, "level"),
        ("magic", None, "kind"),
    ],
)
def test_invalid_assistance_is_rejected(
    practice_dir: Path,
    catalog: Catalog,
    leetcode_two_sum_package: Path,
    kind: str,
    level: int | None,
    fragment: str,
) -> None:
    attempt_id = begin(practice_dir, catalog, leetcode_two_sum_package)
    attempt = find_attempt(load_history(practice_dir), attempt_id)

    with pytest.raises(AttemptError, match=fragment):
        record_assistance(practice_dir, attempt, kind, level, None)

    assert len(load_history(practice_dir).attempts[0].events) == 1


def test_platform_verdict_is_recorded_with_source_and_date_but_no_local_pass(
    practice_dir: Path, catalog: Catalog, leetcode_two_sum_package: Path
) -> None:
    attempt_id = begin(practice_dir, catalog, leetcode_two_sum_package)
    attempt = find_attempt(load_history(practice_dir), attempt_id)

    record_verdict(
        practice_dir, attempt, "accepted", "LeetCode submissions page", "2026-10-28"
    )

    history = load_history(practice_dir)
    event = history.attempts[0].events[-1]
    assert event["type"] == "platform_verdict"
    assert (event["status"], event["source"], event["date"]) == (
        "accepted",
        "LeetCode submissions page",
        "2026-10-28",
    )
    assert view_attempt(history.attempts[0], practice_dir).status == "in_progress"


@pytest.mark.parametrize(
    ("status", "source", "date", "fragment"),
    [
        ("passed", "site", None, "status"),
        ("accepted", "  ", None, "source"),
        ("accepted", "site", "yesterday", "date"),
    ],
)
def test_invalid_verdicts_are_rejected(
    practice_dir: Path,
    catalog: Catalog,
    leetcode_two_sum_package: Path,
    status: str,
    source: str,
    date: str | None,
    fragment: str,
) -> None:
    attempt_id = begin(practice_dir, catalog, leetcode_two_sum_package)
    attempt = find_attempt(load_history(practice_dir), attempt_id)

    with pytest.raises(AttemptError, match=fragment):
        record_verdict(practice_dir, attempt, status, source, date)

    assert len(load_history(practice_dir).attempts[0].events) == 1


def test_verdict_without_a_date_uses_today_in_utc(
    practice_dir: Path, catalog: Catalog, leetcode_two_sum_package: Path
) -> None:
    attempt_id = begin(practice_dir, catalog, leetcode_two_sum_package)
    attempt = find_attempt(load_history(practice_dir), attempt_id)

    record_verdict(practice_dir, attempt, "not_submitted", "my own note", None)

    event = load_history(practice_dir).attempts[0].events[-1]
    assert event["date"] == event["at"][:10]


def test_finishing_an_attempt_keeps_its_code_and_history(
    practice_dir: Path, catalog: Catalog, leetcode_two_sum_package: Path
) -> None:
    attempt_id = begin(practice_dir, catalog, leetcode_two_sum_package)
    attempt = find_attempt(load_history(practice_dir), attempt_id)

    finish_attempt(practice_dir, attempt)

    finished = load_history(practice_dir).attempts[0]
    assert finished.finished_at is not None
    assert attempt_code_path(practice_dir, "leetcode", "1", attempt_id).exists()
