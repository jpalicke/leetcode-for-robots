# ABOUTME: Runs real solutions against the committed LeetCode 704 package and evidence.
# ABOUTME: Blank, defective and alternate solutions must each get the honest outcome.

import shutil
from pathlib import Path

import pytest

from practice.package import ExercisePackage, load_package
from practice.paths import REFERENCES_DIR, REPO_ROOT
from practice.runner import RunResult, run_exercise
from practice.source_manifest import validation_state
from practice.sources import load_manifest, validate_source, verify_references

PACKAGE_DIR = REPO_ROOT / "problems" / "leetcode-704"
SOLUTIONS = REPO_ROOT / "tests" / "fixtures" / "leetcode_binary_search_solutions"
ADAPTER = "neetcode-leetcode-0704-binary-search-python-function-adapter"
ORIGINAL = "original-leetcode-0704-binary-search-half-open-python"
UPSTREAM = "neetcode-leetcode-0704-binary-search-python"


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


# Each wrong-answer solution and one named case that it must fail.
DEFECTS = [
    ("always_minus_one", "platform-example-1"),
    ("returns_value_not_index", "platform-example-1"),
    ("returns_one_based_position", "platform-example-1"),
    ("searches_lower_half_only", "platform-example-1"),
    ("returns_insertion_point", "platform-example-2"),
    ("returns_zero_on_miss", "platform-example-2"),
    ("loop_skips_single_entry_window", "single-element-found"),
    ("misses_first_entry", "target-is-first"),
    ("misses_last_entry", "target-is-last"),
]


@pytest.mark.parametrize(("name", "must_fail"), DEFECTS)
def test_each_defective_solution_fails(
    package: ExercisePackage, name: str, must_fail: str
) -> None:
    result = run(package, SOLUTIONS / f"{name}.py")
    assert result.status == "failed"
    assert outcomes(result)[must_fail] == "failed"


def test_none_for_a_missing_target_is_malformed_not_minus_one(
    package: ExercisePackage,
) -> None:
    result = run(package, SOLUTIONS / "returns_none_on_miss.py")
    assert result.status != "passed"
    assert outcomes(result)["platform-example-2"] == "malformed"


def test_a_float_midpoint_is_a_runtime_error_not_a_pass(
    package: ExercisePackage,
) -> None:
    result = run(package, SOLUTIONS / "float_midpoint.py")
    assert result.status != "passed"
    assert outcomes(result)["platform-example-1"] == "error"


def test_a_window_that_stops_shrinking_ends_in_a_timeout(
    package: ExercisePackage,
) -> None:
    result = run(package, SOLUTIONS / "no_progress_on_miss.py", timeout=5.0)
    assert result.status == "timeout"
    assert outcomes(result)["platform-example-2"] == "timeout"
    assert "platform-example-1" not in outcomes(result)  # The hit before it passed.


@pytest.mark.parametrize(
    "name",
    ["iterative_closed", "recursive_closed", "half_open_loop", "bisect_module"],
)
def test_each_logarithmic_solution_passes(package: ExercisePackage, name: str) -> None:
    result = run(package, SOLUTIONS / f"{name}.py")
    assert result.status == "passed", result.message
    assert outcomes(result) == {}


@pytest.mark.parametrize("name", ["linear_scan", "list_index", "recursive_slicing"])
def test_a_correct_answer_that_reads_too_much_fails_the_probe_budget(
    package: ExercisePackage, name: str
) -> None:
    """The problem asks for O(log n). These are right, and still not accepted."""
    result = run(package, SOLUTIONS / f"{name}.py")
    assert result.status == "failed"
    cases = {c.case_id: c for c in result.cases}
    over = cases["performance-missing-above"]
    assert over.outcome == "failed"
    assert over.probes is not None and over.probes > 1_000
    assert over.probe_budget == 16
    assert "correct answer, but it looked at" in over.detail
    assert "logarithmic" in over.detail
    # Wrong answers elsewhere in the suite are not blamed on the budget.
    assert not any(
        c.outcome == "failed" and "correct answer" not in c.detail for c in result.cases
    )


def test_a_solution_that_checks_both_ends_first_still_fits_the_budget(
    package: ExercisePackage,
) -> None:
    result = run(package, SOLUTIONS / "checks_both_ends_first.py")
    assert result.status == "passed", result.message


def test_the_logarithmic_solutions_read_few_entries_and_the_counts_are_recorded(
    package: ExercisePackage,
) -> None:
    assert package.probe_budget is not None
    assert package.probe_budget.limit(10_000) == 16
    for name in ("iterative_closed", "half_open_loop", "bisect_module"):
        result = run(package, SOLUTIONS / f"{name}.py")
        assert result.status == "passed", name
        for case in result.cases:
            assert case.probes is not None and case.probe_budget is not None
            assert case.probes <= case.probe_budget, (name, case.case_id)
        assert max(c.probes or 0 for c in result.cases) <= 15, name


def test_a_failure_reports_the_case_and_both_answers(package: ExercisePackage) -> None:
    result = run(package, SOLUTIONS / "returns_one_based_position.py")
    failed = next(c for c in result.cases if c.case_id == "platform-example-1")
    assert failed.outcome == "failed"
    assert "5" in failed.detail and "4" in failed.detail


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
    assert result.status == "error"  # No plain search function, and List is unbound.


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
    package_copy = tmp_path / "leetcode-704"
    shutil.copytree(PACKAGE_DIR, package_copy)
    suite = package_copy / "tests.json"
    suite.write_text(
        suite.read_text(encoding="utf-8").replace("leetcode-704-v2", "leetcode-704-v3"),
        encoding="utf-8",
    )
    before = load_manifest(REFERENCES_DIR, ORIGINAL).evidence.local_validation
    again = validate_source(references, ORIGINAL, package_copy)
    assert again.evidence.local_validation.suite_version == "leetcode-704-v3"
    assert again.evidence.local_validation.suite_sha256 != before.suite_sha256
