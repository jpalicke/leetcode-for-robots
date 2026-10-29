# ABOUTME: Runs real solutions against the committed LeetCode 121 package and evidence.
# ABOUTME: Blank, defective and alternate solutions must each get the honest outcome.

import shutil
from pathlib import Path

import pytest

from practice.package import ExercisePackage, load_package
from practice.paths import REFERENCES_DIR, REPO_ROOT
from practice.runner import RunResult, run_exercise
from practice.source_manifest import validation_state
from practice.sources import load_manifest, validate_source, verify_references

PACKAGE_DIR = REPO_ROOT / "problems" / "leetcode-121"
SOLUTIONS = REPO_ROOT / "tests" / "fixtures" / "leetcode_best_time_solutions"
ADAPTER = (
    "neetcode-leetcode-0121-best-time-to-buy-and-sell-stock-python-function-adapter"
)
ORIGINAL = "original-leetcode-0121-highest-price-ahead-python"
UPSTREAM = "neetcode-leetcode-0121-best-time-to-buy-and-sell-stock-python"


@pytest.fixture(scope="module")
def package() -> ExercisePackage:
    return load_package(PACKAGE_DIR)


def run(package: ExercisePackage, solution: Path, timeout: float = 30.0) -> RunResult:
    return run_exercise(package, solution, timeout=timeout)


def outcomes(result: RunResult) -> dict[str, str]:
    return {c.case_id: c.outcome for c in result.cases if c.outcome != "passed"}


def test_a_blank_starter_is_a_stub_and_never_a_pass(package: ExercisePackage) -> None:
    result = run(package, PACKAGE_DIR / "starter.py")
    assert result.status == "stub"


# Each defective solution and one named case that it must fail.
DEFECTS = [
    ("always_zero", "example-buy-then-sell"),
    ("max_minus_min", "global-max-before-global-min"),
    ("last_minus_first", "best-pair-avoids-both-extremes"),
    ("buys_on_first_day_only", "highest-price-is-first"),
    ("can_go_negative", "platform-example-2"),
    ("skips_the_last_day", "sells-on-the-last-day"),
    ("ignores_the_first_day", "buys-on-the-first-day"),
    ("forgets_profit_after_a_new_low", "best-profit-before-a-new-low"),
    ("returns_a_boolean", "platform-example-1"),
]


@pytest.mark.parametrize(("name", "must_fail"), DEFECTS)
def test_each_defective_solution_fails(
    package: ExercisePackage, name: str, must_fail: str
) -> None:
    result = run(package, SOLUTIONS / f"{name}.py")
    assert result.status == "failed"
    assert outcomes(result)[must_fail] == "failed"


@pytest.mark.parametrize(
    "name",
    [
        "lowest_so_far",
        "highest_ahead",
        "daily_differences",
        "accumulate_minimum",
        "sliding_window",
    ],
)
def test_each_alternate_solution_passes(package: ExercisePackage, name: str) -> None:
    result = run(package, SOLUTIONS / f"{name}.py")
    assert result.status == "passed", result.message
    assert outcomes(result) == {}


def test_the_quadratic_solution_is_a_timeout_not_a_pass(
    package: ExercisePackage,
) -> None:
    result = run(package, SOLUTIONS / "brute_force.py", timeout=8.0)
    assert result.status == "timeout"
    timed_out = [c.case_id for c in result.cases if c.outcome == "timeout"]
    assert timed_out and timed_out[0].startswith("performance-")
    # Every case before the first maximum-length one was answered correctly.
    assert "platform-example-1" not in outcomes(result)
    assert "generated-wide-01" not in outcomes(result)


def test_a_failure_reports_the_case_and_both_answers(package: ExercisePackage) -> None:
    result = run(package, SOLUTIONS / "max_minus_min.py")
    failed = next(c for c in result.cases if c.case_id == "platform-example-1")
    assert failed.outcome == "failed"
    assert "6" in failed.detail and "5" in failed.detail


def test_the_committed_references_run_and_pass_on_the_current_suite(
    package: ExercisePackage,
) -> None:
    for source in (ADAPTER, ORIGINAL):
        manifest = load_manifest(REFERENCES_DIR, source)
        result = run(package, REFERENCES_DIR / manifest.file.path)
        assert result.status == "passed", source
        recorded = manifest.evidence.local_validation
        assert recorded.code_sha256 == result.code_sha256
        assert recorded.suite_sha256 == result.suite_sha256


def test_recorded_evidence_is_current_and_acceptance_is_still_none() -> None:
    assert verify_references(REFERENCES_DIR).problems == []
    for source in (ADAPTER, ORIGINAL):
        manifest = load_manifest(REFERENCES_DIR, source)
        assert validation_state(manifest) == "current"
        assert manifest.evidence.local_validation.status == "passed"
        assert manifest.evidence.platform_acceptance.status == "none"
    upstream = load_manifest(REFERENCES_DIR, UPSTREAM)
    assert upstream.evidence.local_validation.status == "none"  # Cannot run as stored.
    assert upstream.evidence.platform_acceptance.status == "none"


def test_the_upstream_file_alone_cannot_run_so_the_adapter_exists(
    package: ExercisePackage,
) -> None:
    upstream = load_manifest(REFERENCES_DIR, UPSTREAM)
    result = run(package, REFERENCES_DIR / upstream.file.path)
    assert result.status == "error"  # No plain maxProfit function, and List is unbound.


def test_the_adapter_contains_the_upstream_bytes_unchanged() -> None:
    upstream = load_manifest(REFERENCES_DIR, UPSTREAM)
    adapter = load_manifest(REFERENCES_DIR, ADAPTER)
    original_bytes = (REFERENCES_DIR / upstream.file.path).read_bytes()
    adapted_bytes = (REFERENCES_DIR / adapter.file.path).read_bytes()
    assert original_bytes in adapted_bytes
    assert adapted_bytes.startswith(b"from typing import List\n")
    assert adapter.derived_from == UPSTREAM


def test_a_changed_suite_makes_recorded_evidence_for_another_suite(
    tmp_path: Path,
) -> None:
    references = tmp_path / "references"
    shutil.copytree(REFERENCES_DIR, references)
    package_copy = tmp_path / "leetcode-121"
    shutil.copytree(PACKAGE_DIR, package_copy)
    suite = package_copy / "tests.json"
    suite.write_text(
        suite.read_text(encoding="utf-8").replace("leetcode-121-v1", "leetcode-121-v2"),
        encoding="utf-8",
    )
    before = load_manifest(REFERENCES_DIR, ORIGINAL).evidence.local_validation
    again = validate_source(references, ORIGINAL, package_copy)
    assert again.evidence.local_validation.suite_version == "leetcode-121-v2"
    assert again.evidence.local_validation.suite_sha256 != before.suite_sha256
