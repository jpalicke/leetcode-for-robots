# ABOUTME: Drives the whole LeetCode 704 learner flow through the practice CLI.
# ABOUTME: Uses the committed package with no --package flag and a temp practice dir.

import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

from practice.paths import REPO_ROOT

PACKAGE = REPO_ROOT / "problems" / "leetcode-704"
SOLUTIONS = REPO_ROOT / "tests" / "fixtures" / "leetcode_binary_search_solutions"


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
    started = practice(practice_dir, "attempt", "start", "leetcode", "704")
    assert started.returncode == 0, started.stderr
    attempt_id = re.search(r"Started attempt (\S+)", started.stdout)
    code = re.search(r"^Code: (.+)$", started.stdout, re.MULTILINE)
    assert attempt_id is not None and code is not None, started.stdout
    return attempt_id.group(1), Path(code.group(1))


def case_count() -> int:
    suite = json.loads((PACKAGE / "tests.json").read_text(encoding="utf-8"))
    return len(suite["cases"])


def test_search_finds_the_problem(tmp_path: Path) -> None:
    result = practice(tmp_path, "search", "binary search")
    assert result.returncode == 0, result.stderr
    assert "704" in result.stdout
    assert "binary-search" in result.stdout


def test_start_copies_the_starter_byte_for_byte(tmp_path: Path) -> None:
    _, code = start(tmp_path)
    assert code.read_bytes() == (PACKAGE / "starter.py").read_bytes()


def test_the_full_flow_from_blank_to_a_passing_attempt(tmp_path: Path) -> None:
    attempt_id, code = start(tmp_path)

    blank = practice(tmp_path, "attempt", "test", attempt_id)
    assert blank.returncode == 1
    assert "STUB" in blank.stdout

    shutil.copyfile(SOLUTIONS / "misses_last_entry.py", code)
    wrong = practice(tmp_path, "attempt", "test", attempt_id)
    assert wrong.returncode == 1
    assert "FAILED" in wrong.stdout
    assert "target-is-last" in wrong.stdout

    shutil.copyfile(SOLUTIONS / "iterative_closed.py", code)
    right = practice(tmp_path, "attempt", "test", attempt_id)
    assert right.returncode == 0, right.stdout
    assert f"PASSED  leetcode/704: all {case_count()} cases passed" in right.stdout

    progress = practice(tmp_path, "progress", "leetcode", "704")
    assert progress.returncode == 0, progress.stderr
    assert "passed locally" in progress.stdout
    assert "platform verdict: none recorded" in progress.stdout

    notes = practice(tmp_path, "notes", attempt_id)
    assert "stub" in notes.stdout
    assert "failed" in notes.stdout
    assert "passed" in notes.stdout


@pytest.mark.parametrize(
    "name", ["recursive_closed", "half_open_loop", "bisect_module"]
)
def test_alternate_approaches_pass_through_the_cli(tmp_path: Path, name: str) -> None:
    attempt_id, code = start(tmp_path)
    shutil.copyfile(SOLUTIONS / f"{name}.py", code)
    result = practice(tmp_path, "attempt", "test", attempt_id)
    assert result.returncode == 0, result.stdout
    assert "PASSED" in result.stdout


def test_a_correct_linear_attempt_fails_with_the_count_it_read(tmp_path: Path) -> None:
    attempt_id, code = start(tmp_path)
    shutil.copyfile(SOLUTIONS / "linear_scan.py", code)
    result = practice(tmp_path, "attempt", "test", attempt_id)
    assert result.returncode == 1
    assert "PASSED" not in result.stdout
    assert "FAILED" in result.stdout
    assert "correct answer, but it looked at 10,000 of 10,000 entries" in result.stdout
    assert "allows up to 16" in result.stdout
    # The same attempt id, rewritten as a halving search, passes.
    shutil.copyfile(SOLUTIONS / "iterative_closed.py", code)
    again = practice(tmp_path, "attempt", "test", attempt_id)
    assert again.returncode == 0, again.stdout
    assert "PASSED" in again.stdout


def test_run_json_carries_the_counts(tmp_path: Path) -> None:
    result = practice(
        tmp_path,
        "run",
        str(PACKAGE),
        str(SOLUTIONS / "iterative_closed.py"),
        "--json",
    )
    assert result.returncode == 0, result.stdout + result.stderr
    cases = json.loads(result.stdout)["cases"]
    assert all(c["probe_budget"] is not None for c in cases)
    assert all(c["probes"] <= c["probe_budget"] for c in cases)
    assert max(c["probes"] for c in cases) <= 15


def test_a_crashing_attempt_is_reported_and_never_passes(tmp_path: Path) -> None:
    attempt_id, code = start(tmp_path)
    shutil.copyfile(SOLUTIONS / "float_midpoint.py", code)
    result = practice(tmp_path, "attempt", "test", attempt_id)
    assert result.returncode == 1
    assert "PASSED" not in result.stdout


def test_the_committed_references_verify_through_the_cli(tmp_path: Path) -> None:
    check = practice(tmp_path, "sources", "verify")
    assert check.returncode == 0, check.stderr
    assert re.search(r"\d+ source\(s\) verified", check.stdout)


def test_readiness_reports_ready_and_the_untested_requirement(tmp_path: Path) -> None:
    result = practice(tmp_path, "readiness", "leetcode", "704", "--json")
    assert result.returncode == 0, result.stdout
    report = json.loads(result.stdout)
    assert report["ready"] is True
    assert [c["name"] for c in report["checks"] if not c["ok"]] == []
    assert report["platform_acceptance"] == "none"
    verified = " ".join(item["against"] for item in report["verification"]["verified"])
    assert "live LeetCode GraphQL" in verified
    not_verified = " ".join(report["verification"]["not_verified"])
    assert "does not prove" in not_verified
    assert "not enforced" not in not_verified
    text = practice(tmp_path, "readiness", "leetcode", "704")
    assert "READY  leetcode/704" in text.stdout
