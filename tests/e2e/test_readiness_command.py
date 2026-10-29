# ABOUTME: End-to-end tests that run `practice readiness` in a subprocess.
# ABOUTME: Covers the committed package, a broken copy, JSON output and bad input.

import json
import shutil
import subprocess
import sys
from pathlib import Path

from practice.paths import REPO_ROOT


def run_practice(*args: str) -> subprocess.CompletedProcess[str]:
    scripts = Path(sys.executable).parent
    command = next(
        path
        for name in ("practice.exe", "practice")
        if (path := scripts / name).exists()
    )
    return subprocess.run(
        [str(command), *args],
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=120,
        check=False,
    )


def test_the_committed_package_reports_ready() -> None:
    result = run_practice("readiness", "leetcode", "1")
    assert result.returncode == 0, result.stderr
    assert "READY  leetcode/1" in result.stdout
    assert "platform acceptance: none" in result.stdout
    assert "not verified:" in result.stdout


def test_json_output_is_the_machine_readable_report() -> None:
    result = run_practice("readiness", "leetcode", "1", "--json")
    assert result.returncode == 0, result.stderr
    report = json.loads(result.stdout)
    assert report["ready"] is True
    assert report["platform_acceptance"] == "none"
    assert {check["name"] for check in report["checks"]} >= {"starter", "evidence"}
    assert report["verification"]["not_verified"]


def test_a_broken_copy_exits_one_and_names_the_failure(tmp_path: Path) -> None:
    package = tmp_path / "copy"
    shutil.copytree(REPO_ROOT / "problems" / "leetcode-1", package)
    (package / "hints" / "1.md").unlink()
    result = run_practice("readiness", "leetcode", "1", "--package", str(package))
    assert result.returncode == 1
    assert "NOT READY  leetcode/1" in result.stdout
    assert "FAIL  hints" in result.stdout


def test_a_missing_package_is_bad_input(tmp_path: Path) -> None:
    result = run_practice(
        "readiness", "leetcode", "1", "--package", str(tmp_path / "missing")
    )
    assert result.returncode == 3
    assert "not a directory" in result.stderr
