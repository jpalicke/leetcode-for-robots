# ABOUTME: Tests the readiness report against copies of the committed Two Sum package.
# ABOUTME: Each check is broken on purpose in a temporary copy and must be reported.

import json
import shutil
from collections.abc import Callable
from pathlib import Path
from typing import Any

import pytest

from practice.paths import REFERENCES_DIR, REPO_ROOT
from practice.readiness import ReadinessReport, check_readiness

PACKAGE = REPO_ROOT / "problems" / "leetcode-1"


@pytest.fixture
def copies(tmp_path: Path) -> tuple[Path, Path]:
    package = tmp_path / "leetcode-1"
    references = tmp_path / "references"
    shutil.copytree(PACKAGE, package)
    shutil.copytree(REFERENCES_DIR, references)
    return package, references


def failed(report: ReadinessReport) -> list[str]:
    return [check.name for check in report.checks if not check.ok]


def edit_record(package: Path, change: Callable[[dict[str, Any]], None]) -> None:
    path = package / "readiness.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    change(data)
    path.write_text(json.dumps(data), encoding="utf-8")


def edit_hint_index(package: Path, change: Callable[[dict[str, Any]], None]) -> None:
    path = package / "hints" / "index.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    change(data)
    path.write_text(json.dumps(data), encoding="utf-8")


def test_the_committed_package_is_ready() -> None:
    report = check_readiness(PACKAGE, REFERENCES_DIR)
    assert failed(report) == []
    assert report.ready
    assert report.platform_acceptance == "none"


def test_the_report_names_every_check_once() -> None:
    names = [c.name for c in check_readiness(PACKAGE, REFERENCES_DIR).checks]
    assert len(names) == len(set(names))
    for expected in ("package", "starter", "hints", "references", "evidence"):
        assert expected in names


def test_a_missing_record_is_not_ready(copies: tuple[Path, Path]) -> None:
    package, references = copies
    (package / "readiness.json").unlink()
    report = check_readiness(package, references)
    assert not report.ready
    assert "record" in failed(report)


def test_a_starter_with_a_real_body_is_not_ready(copies: tuple[Path, Path]) -> None:
    package, references = copies
    (package / "starter.py").write_text(
        "def twoSum(nums, target):\n    return [0, 1]\n", encoding="utf-8"
    )
    assert "starter" in failed(check_readiness(package, references))


def test_a_hint_with_the_wrong_spoiler_flag_is_not_ready(
    copies: tuple[Path, Path],
) -> None:
    package, references = copies
    edit_hint_index(package, lambda data: data["hints"][0].update(spoiler=False))
    assert "hints" in failed(check_readiness(package, references))


def test_a_missing_hint_file_is_not_ready(copies: tuple[Path, Path]) -> None:
    package, references = copies
    (package / "hints" / "2.md").unlink()
    assert "hints" in failed(check_readiness(package, references))


def test_naming_the_technique_before_the_last_level_is_not_ready(
    copies: tuple[Path, Path],
) -> None:
    package, references = copies
    edit_hint_index(package, lambda data: data["hints"][1].update(names_technique=True))
    assert "hints" in failed(check_readiness(package, references))


def test_a_spoiler_file_labelled_open_is_not_ready(copies: tuple[Path, Path]) -> None:
    package, references = copies
    edit_record(
        package,
        lambda data: data["files"]["notes"].update(content_class="statement_summary"),
    )
    assert "files" in failed(check_readiness(package, references))


def test_a_changed_suite_makes_reference_evidence_stale(
    copies: tuple[Path, Path],
) -> None:
    package, references = copies
    suite = json.loads((package / "tests.json").read_text(encoding="utf-8"))
    suite["version"] = "leetcode-1-v2"
    (package / "tests.json").write_text(json.dumps(suite), encoding="utf-8")
    report = check_readiness(package, references)
    assert "evidence" in failed(report)
    assert not report.ready


def test_changed_reference_code_makes_evidence_stale(
    copies: tuple[Path, Path],
) -> None:
    package, references = copies
    code = next(
        (
            references
            / "original"
            / "original-leetcode-0001-two-sum-sorted-pointers-python"
        ).rglob("*.py")
    )
    code.write_text(code.read_text(encoding="utf-8") + "\n# edited\n", encoding="utf-8")
    report = check_readiness(package, references)
    assert "references" in failed(report)
    assert not report.ready


def test_a_listed_blocker_is_not_ready(copies: tuple[Path, Path]) -> None:
    package, references = copies
    edit_record(package, lambda data: data.update(blockers=["No Python 3 runner"]))
    report = check_readiness(package, references)
    assert "blockers" in failed(report)
    assert report.blockers == ["No Python 3 runner"]


def test_an_unlisted_reference_is_reported(copies: tuple[Path, Path]) -> None:
    package, references = copies
    edit_record(
        package,
        lambda data: data["references"].update(originals=["no-such-source"]),
    )
    assert "references" in failed(check_readiness(package, references))


def test_a_mismatched_record_identity_is_not_ready(copies: tuple[Path, Path]) -> None:
    package, references = copies
    edit_record(package, lambda data: data.update(problem_id="2"))
    assert "record" in failed(check_readiness(package, references))
