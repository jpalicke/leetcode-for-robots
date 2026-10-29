# ABOUTME: Runs real solutions against the committed LeetCode 1 package and evidence.
# ABOUTME: Blank, defective and alternate solutions must each get the honest outcome.

import json
import shutil
from pathlib import Path

import pytest

from practice.package import ExercisePackage, load_package
from practice.paths import REFERENCES_DIR, REPO_ROOT
from practice.runner import RunResult, run_exercise
from practice.source_manifest import sha256_hex, validation_state
from practice.sources import load_manifest, validate_source, verify_references

PACKAGE_DIR = REPO_ROOT / "problems" / "leetcode-1"
SOLUTIONS = REPO_ROOT / "tests" / "fixtures" / "leetcode_two_sum_solutions"
ADAPTER = "neetcode-leetcode-0001-two-sum-python-function-adapter"
ORIGINAL = "original-leetcode-0001-two-sum-sorted-pointers-python"
UPSTREAM = "neetcode-leetcode-0001-two-sum-python"


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
    ("wrong_answer", "example-ascending"),
    ("off_by_one", "pair-at-the-end"),
    ("reuses_same_element", "half-of-target-appears-once"),
    ("returns_values", "example-unsorted"),
    ("skips_duplicate_values", "duplicate-pair-only"),
    ("positives_only", "all-negative"),
]


@pytest.mark.parametrize(("name", "must_fail"), DEFECTS)
def test_each_defective_solution_fails(
    package: ExercisePackage, name: str, must_fail: str
) -> None:
    result = run(package, SOLUTIONS / f"{name}.py")
    assert result.status == "failed"
    assert must_fail in failing_ids(result)


@pytest.mark.parametrize(
    "name",
    [
        "hash_map",
        "two_pass_hash_map",
        "brute_force",
        "sort_and_pointers",
        "reversed_order",
        "larger_index_first",
    ],
)
def test_each_alternate_solution_passes(package: ExercisePackage, name: str) -> None:
    result = run(package, SOLUTIONS / f"{name}.py")
    assert result.status == "passed", result.message
    assert failing_ids(result) == set()


def test_the_quadratic_solution_finishes_well_inside_the_default_timeout(
    package: ExercisePackage,
) -> None:
    result = run_exercise(package, SOLUTIONS / "brute_force.py")  # Default 10 s.
    assert result.status == "passed"
    assert result.duration_seconds < result.timeout_seconds


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
    assert result.status == "error"  # No plain twoSum function in the class-only file.


def test_evidence_goes_stale_when_the_reference_code_changes(tmp_path: Path) -> None:
    references = tmp_path / "references"
    shutil.copytree(REFERENCES_DIR, references)
    manifest = load_manifest(references, ORIGINAL)
    code = references / manifest.file.path
    code.write_bytes(code.read_bytes() + b"\n# edited\n")
    # The file hash no longer matches the manifest, so verification refuses it.
    problems = verify_references(references).problems
    assert any(ORIGINAL in p and "sha256 mismatch" in p for p in problems)


def test_revalidating_changed_code_replaces_the_old_evidence(tmp_path: Path) -> None:
    references = tmp_path / "references"
    shutil.copytree(REFERENCES_DIR, references)
    before = load_manifest(references, ORIGINAL).evidence.local_validation
    # A comment-only edit, with the manifest's file hash updated to match it.
    manifest = load_manifest(references, ORIGINAL)
    code = references / manifest.file.path
    changed = code.read_bytes() + b"\n# edited\n"
    code.write_bytes(changed)
    path = references / "manifests" / f"{ORIGINAL}.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    data["file"]["sha256"] = sha256_hex(changed)  # Only the file, not the evidence.
    path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    stale = load_manifest(references, ORIGINAL)
    assert validation_state(stale) == "stale"
    assert any("stale" in p for p in verify_references(references).problems)
    again = validate_source(references, ORIGINAL, PACKAGE_DIR)
    assert validation_state(again) == "current"
    assert again.evidence.local_validation.code_sha256 != before.code_sha256
    assert verify_references(references).problems == []
