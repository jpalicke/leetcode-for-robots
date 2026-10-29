# ABOUTME: Drives the whole LeetCode 1 learner flow through the practice CLI subprocess.
# ABOUTME: Uses the committed package with no --package flag and a temp practice dir.

import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

from practice.paths import REPO_ROOT

PACKAGE = REPO_ROOT / "problems" / "leetcode-1"
SOLUTIONS = REPO_ROOT / "tests" / "fixtures" / "leetcode_two_sum_solutions"


def practice(
    practice_dir: Path, *args: str, timeout: int = 120
) -> subprocess.CompletedProcess[str]:
    scripts = Path(sys.executable).parent
    command = next(
        path
        for name in ("practice.exe", "practice")
        if (path := scripts / name).exists()
    )
    environment = os.environ.copy()
    environment["PRACTICE_DIR"] = str(practice_dir)
    return subprocess.run(
        [str(command), *args],
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=timeout,
        check=False,
        env=environment,
    )


def start(practice_dir: Path) -> tuple[str, Path]:
    started = practice(practice_dir, "attempt", "start", "leetcode", "1")
    assert started.returncode == 0, started.stderr
    attempt_id = re.search(r"Started attempt (\S+)", started.stdout)
    code = re.search(r"^Code: (.+)$", started.stdout, re.MULTILINE)
    assert attempt_id is not None and code is not None, started.stdout
    return attempt_id.group(1), Path(code.group(1))


def test_search_finds_the_problem(tmp_path: Path) -> None:
    result = practice(tmp_path, "search", "two sum")
    assert result.returncode == 0, result.stderr
    assert "Two Sum" in result.stdout
    assert "two-sum" in result.stdout


def test_start_copies_the_starter_byte_for_byte(tmp_path: Path) -> None:
    _, code = start(tmp_path)
    assert code.read_bytes() == (PACKAGE / "starter.py").read_bytes()


def test_the_full_flow_from_blank_to_a_passing_attempt(tmp_path: Path) -> None:
    attempt_id, code = start(tmp_path)

    blank = practice(tmp_path, "attempt", "test", attempt_id)
    assert blank.returncode == 1
    assert "STUB" in blank.stdout

    shutil.copyfile(SOLUTIONS / "off_by_one.py", code)
    wrong = practice(tmp_path, "attempt", "test", attempt_id)
    assert wrong.returncode == 1
    assert "FAILED" in wrong.stdout
    assert "pair-at-the-end" in wrong.stdout

    shutil.copyfile(SOLUTIONS / "hash_map.py", code)
    right = practice(tmp_path, "attempt", "test", attempt_id)
    assert right.returncode == 0, right.stdout
    assert "PASSED  leetcode/1: all 71 cases passed" in right.stdout

    progress = practice(tmp_path, "progress", "leetcode", "1")
    assert progress.returncode == 0, progress.stderr
    assert "passed locally" in progress.stdout
    assert "platform verdict: none recorded" in progress.stdout

    notes = practice(tmp_path, "notes", attempt_id)
    assert "stub" in notes.stdout
    assert "failed" in notes.stdout
    assert "passed" in notes.stdout


@pytest.mark.parametrize(
    "name", ["brute_force", "sort_and_pointers", "reversed_order", "larger_index_first"]
)
def test_alternate_approaches_pass_through_the_cli(tmp_path: Path, name: str) -> None:
    attempt_id, code = start(tmp_path)
    shutil.copyfile(SOLUTIONS / f"{name}.py", code)
    result = practice(tmp_path, "attempt", "test", attempt_id)
    assert result.returncode == 0, result.stdout
    assert "PASSED" in result.stdout


def test_the_committed_references_verify_through_the_cli(tmp_path: Path) -> None:
    check = practice(tmp_path, "sources", "verify")
    assert check.returncode == 0, check.stderr
    assert re.search(r"\d+ source\(s\) verified", check.stdout)


def test_readiness_reports_ready_with_no_platform_acceptance(tmp_path: Path) -> None:
    result = practice(tmp_path, "readiness", "leetcode", "1")
    assert result.returncode == 0, result.stdout
    assert "READY" in result.stdout
    assert "none" in result.stdout
