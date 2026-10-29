# ABOUTME: Runs real solutions against the committed LeetCode 242 package and evidence.
# ABOUTME: Blank, defective and alternate solutions must each get the honest outcome.

import shutil
from pathlib import Path

import pytest

from practice.package import ExercisePackage, load_package
from practice.paths import REFERENCES_DIR, REPO_ROOT
from practice.runner import RunResult, run_exercise
from practice.source_manifest import validation_state
from practice.sources import load_manifest, validate_source, verify_references

PACKAGE_DIR = REPO_ROOT / "problems" / "leetcode-242"
SOLUTIONS = REPO_ROOT / "tests" / "fixtures" / "leetcode_valid_anagram_solutions"
ADAPTER = "neetcode-leetcode-0242-valid-anagram-python-function-adapter"
ORIGINAL = "original-leetcode-0242-valid-anagram-letter-counts-python"
UPSTREAM = "neetcode-leetcode-0242-valid-anagram-python"


@pytest.fixture(scope="module")
def package() -> ExercisePackage:
    return load_package(PACKAGE_DIR)


def run(package: ExercisePackage, solution: Path) -> RunResult:
    return run_exercise(package, solution, timeout=30.0)


def failing_ids(result: RunResult) -> set[str]:
    return {case.case_id for case in result.cases if case.outcome != "passed"}


def test_a_blank_starter_is_a_stub_and_never_a_pass(package: ExercisePackage) -> None:
    result = run(package, PACKAGE_DIR / "starter.py")
    assert result.status == "stub"


# Each defective solution and one named case that it must fail.
DEFECTS = [
    ("always_false", "example-anagram"),
    ("always_true", "single-letter-different"),
    ("compares_letter_sets", "same-letters-different-counts"),
    ("compares_lengths_only", "same-length-different-letters"),
    ("sums_letter_codes", "same-total-of-letter-codes"),
    ("ignores_last_letter", "differs-in-the-last-letter"),
    ("ignores_first_letter", "differs-in-the-first-letter"),
    ("skips_length_check", "different-lengths-prefix"),
    ("returns_integers", "example-anagram"),
]


@pytest.mark.parametrize(("name", "must_fail"), DEFECTS)
def test_each_defective_solution_fails(
    package: ExercisePackage, name: str, must_fail: str
) -> None:
    result = run(package, SOLUTIONS / f"{name}.py")
    assert result.status == "failed"
    assert must_fail in failing_ids(result)


@pytest.mark.parametrize(
    "name", ["sorted_letters", "counter", "dict_counts", "count_per_letter"]
)
def test_each_alternate_solution_passes(package: ExercisePackage, name: str) -> None:
    result = run(package, SOLUTIONS / f"{name}.py")
    assert result.status == "passed", result.message
    assert failing_ids(result) == set()


def test_a_failure_reports_the_case_and_both_answers(package: ExercisePackage) -> None:
    result = run(package, SOLUTIONS / "always_false.py")
    failed = next(c for c in result.cases if c.case_id == "example-anagram")
    assert failed.outcome == "failed"
    assert "false" in failed.detail.lower()
    assert "true" in failed.detail.lower()


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
    assert result.status == "error"  # No plain isAnagram function.


def test_the_adapter_keeps_the_upstream_bytes_as_its_prefix() -> None:
    upstream = load_manifest(REFERENCES_DIR, UPSTREAM)
    adapter = load_manifest(REFERENCES_DIR, ADAPTER)
    original_bytes = (REFERENCES_DIR / upstream.file.path).read_bytes()
    adapted_bytes = (REFERENCES_DIR / adapter.file.path).read_bytes()
    assert adapted_bytes.startswith(original_bytes)
    assert adapter.derived_from == UPSTREAM


def test_a_changed_suite_makes_recorded_evidence_for_another_suite(
    tmp_path: Path,
) -> None:
    references = tmp_path / "references"
    shutil.copytree(REFERENCES_DIR, references)
    package_copy = tmp_path / "leetcode-242"
    shutil.copytree(PACKAGE_DIR, package_copy)
    suite = package_copy / "tests.json"
    suite.write_text(
        suite.read_text(encoding="utf-8").replace("leetcode-242-v1", "leetcode-242-v2"),
        encoding="utf-8",
    )
    before = load_manifest(REFERENCES_DIR, ORIGINAL).evidence.local_validation
    again = validate_source(references, ORIGINAL, package_copy)
    assert again.evidence.local_validation.suite_version == "leetcode-242-v2"
    assert again.evidence.local_validation.suite_sha256 != before.suite_sha256
