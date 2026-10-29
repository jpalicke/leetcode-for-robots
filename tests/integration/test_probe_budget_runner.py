# ABOUTME: Runs real solutions under a probe budget in real child processes.
# ABOUTME: Correct but linear answers must fail with the count; logarithmic ones pass.

import json
from collections.abc import Callable
from pathlib import Path
from typing import Any

import pytest

from practice.package import ExercisePackage, load_package
from practice.runner import CaseResult, RunResult, run_exercise

BIG = list(range(0, 4_000, 2))  # 2,000 entries: the budget is 11 + 2 = 13.
HUGE = list(range(0, 20_000, 2))  # 10,000 entries: the budget is 14 + 2 = 16.
METADATA: dict[str, Any] = {
    "platform": "fixture",
    "id": "search-fixture",
    "title": "Search",
    "language": "python",
    "callable": {
        "adapter": "function",
        "name": "search",
        "parameters": ["nums", "target"],
    },
    "checker": "exact",
    "probe_budget": {"argument": "nums", "growth": "log2", "slack": 2},
}
SUITE: dict[str, Any] = {
    "version": "fixture-1",
    "cases": [
        {"id": "tiny-found", "args": [[1, 3, 5], 3], "expected": 1},
        {"id": "tiny-missing", "args": [[1, 3, 5], 4], "expected": -1},
        {"id": "single", "args": [[7], 7], "expected": 0},
        {"id": "big-first", "args": [BIG, 0], "expected": 0},
        {"id": "big-last", "args": [BIG, 3_998], "expected": 1_999},
        {"id": "big-middle", "args": [BIG, 2_000], "expected": 1_000},
        {"id": "big-missing", "args": [BIG, 2_001], "expected": -1},
        {"id": "huge-missing-above", "args": [HUGE, 20_001], "expected": -1},
    ],
}
LOGARITHMIC = """
def search(nums, target):
    left, right = 0, len(nums) - 1
    while left <= right:
        mid = (left + right) // 2
        if nums[mid] > target:
            right = mid - 1
        elif nums[mid] < target:
            left = mid + 1
        else:
            return mid
    return -1
"""
BISECT = """
from bisect import bisect_left


def search(nums, target):
    spot = bisect_left(nums, target)
    return spot if spot < len(nums) and nums[spot] == target else -1
"""
LINEAR = """
def search(nums, target):
    for index, value in enumerate(nums):
        if value == target:
            return index
    return -1
"""
LIST_INDEX = """
def search(nums, target):
    return nums.index(target) if target in nums else -1
"""
SLICING = """
def search(nums, target):
    def look(part, offset):
        if not part:
            return -1
        mid = len(part) // 2
        if part[mid] == target:
            return offset + mid
        if part[mid] < target:
            return look(part[mid + 1:], offset + mid + 1)
        return look(part[:mid], offset)

    return look(nums, 0)
"""
SORTS_A_COPY = """
def search(nums, target):
    ordered = sorted(nums)
    low, high = 0, len(ordered) - 1
    while low <= high:
        mid = (low + high) // 2
        if ordered[mid] < target:
            low = mid + 1
        elif ordered[mid] > target:
            high = mid - 1
        else:
            return mid
    return -1
"""
WRONG_BUT_FAST = """
def search(nums, target):
    return -1
"""
WRONG_AND_SLOW = """
def search(nums, target):
    return sum(nums) * 0 - 2
"""
CRASHES = """
def search(nums, target):
    return nums[len(nums)]
"""


@pytest.fixture
def budgeted(make_package: Callable[..., Path]) -> ExercisePackage:
    return load_package(make_package(METADATA, SUITE))


def solution(tmp_path: Path, source: str) -> Path:
    path = tmp_path / "solution.py"
    path.write_text(source, encoding="utf-8")
    return path


def by_id(result: RunResult) -> dict[str, CaseResult]:
    return {case.case_id: case for case in result.cases}


def test_a_logarithmic_search_passes_and_the_counts_are_recorded(
    budgeted: ExercisePackage, tmp_path: Path
) -> None:
    result = run_exercise(budgeted, solution(tmp_path, LOGARITHMIC), timeout=30)
    assert result.status == "passed", result.message
    cases = by_id(result)
    for case in result.cases:
        assert case.probes is not None and case.probe_budget is not None
        assert case.probes <= case.probe_budget
    assert cases["big-missing"].probe_budget == 13
    assert cases["huge-missing-above"].probe_budget == 16
    assert cases["single"].probe_budget == 3
    assert 1 <= (cases["big-missing"].probes or 0) <= 11


def test_the_standard_library_search_passes(
    budgeted: ExercisePackage, tmp_path: Path
) -> None:
    result = run_exercise(budgeted, solution(tmp_path, BISECT), timeout=30)
    assert result.status == "passed", result.message


@pytest.mark.parametrize("source", [LINEAR, LIST_INDEX, SLICING, SORTS_A_COPY])
def test_a_correct_answer_that_reads_too_much_fails_with_the_count(
    budgeted: ExercisePackage, tmp_path: Path, source: str
) -> None:
    result = run_exercise(budgeted, solution(tmp_path, source), timeout=30)
    assert result.status == "failed"
    over = by_id(result)["big-missing"]
    assert over.outcome == "failed"
    assert over.probes is not None and over.probes > 13
    assert "correct answer" in over.detail
    assert f"looked at {over.probes:,} of 2,000 entries" in over.detail
    assert "allows up to 13" in over.detail
    assert "logarithmic" in over.detail


def test_a_linear_scan_gets_the_exact_message_on_a_missing_target(
    budgeted: ExercisePackage, tmp_path: Path
) -> None:
    result = run_exercise(budgeted, solution(tmp_path, LINEAR), timeout=30)
    over = by_id(result)["huge-missing-above"]
    assert over.probes == 10_000
    assert over.probe_budget == 16
    assert "looked at 10,000 of 10,000 entries" in over.detail
    assert "needs about 14" in over.detail


def test_only_the_cases_that_read_too_much_fail(
    budgeted: ExercisePackage, tmp_path: Path
) -> None:
    result = run_exercise(budgeted, solution(tmp_path, LINEAR), timeout=30)
    cases = by_id(result)
    assert cases["tiny-found"].outcome == "passed"  # Three entries are within 5.
    assert cases["single"].outcome == "passed"
    assert cases["big-first"].outcome == "passed"  # It found it at the front.
    assert cases["big-last"].outcome == "failed"
    assert cases["big-missing"].outcome == "failed"


def test_a_wrong_answer_reports_the_wrong_answer_not_the_budget(
    budgeted: ExercisePackage, tmp_path: Path
) -> None:
    fast = run_exercise(budgeted, solution(tmp_path, WRONG_BUT_FAST), timeout=30)
    wrong = by_id(fast)["tiny-found"]
    assert wrong.outcome == "failed"
    assert "looked at" not in wrong.detail
    slow = run_exercise(budgeted, solution(tmp_path, WRONG_AND_SLOW), timeout=30)
    still_wrong = by_id(slow)["big-missing"]
    assert still_wrong.outcome == "failed"
    assert "looked at" not in still_wrong.detail  # The answer was judged first.


def test_a_crash_is_an_error_not_a_budget_failure(
    budgeted: ExercisePackage, tmp_path: Path
) -> None:
    result = run_exercise(budgeted, solution(tmp_path, CRASHES), timeout=30)
    assert result.status == "error"
    crashed = by_id(result)["tiny-found"]
    assert crashed.outcome == "error"
    assert crashed.probes is None


def test_the_counts_are_in_the_json_form_of_the_result(
    budgeted: ExercisePackage, tmp_path: Path
) -> None:
    result = run_exercise(budgeted, solution(tmp_path, LINEAR), timeout=30)
    data = json.loads(json.dumps(result.to_dict()))
    case = next(c for c in data["cases"] if c["case_id"] == "big-missing")
    assert case["probes"] == 2_000
    assert case["probe_budget"] == 13


def test_a_package_without_a_budget_behaves_as_before(
    make_package: Callable[..., Path], tmp_path: Path
) -> None:
    metadata = {k: v for k, v in METADATA.items() if k != "probe_budget"}
    package = load_package(make_package(metadata, SUITE))
    result = run_exercise(package, solution(tmp_path, LINEAR), timeout=30)
    assert result.status == "passed", result.message
    for case in result.cases:
        assert case.probes is None and case.probe_budget is None


def test_the_argument_is_a_fresh_list_for_every_case(
    budgeted: ExercisePackage, tmp_path: Path
) -> None:
    """Counts from one case never leak into the next."""
    result = run_exercise(budgeted, solution(tmp_path, LOGARITHMIC), timeout=30)
    cases = by_id(result)
    assert (cases["tiny-found"].probes or 0) <= 3
    assert (cases["single"].probes or 0) == 1
