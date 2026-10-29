# ABOUTME: Drives the whole LeetCode 217 learner flow through the practice CLI.
# ABOUTME: Uses the committed package with no --package flag and a temp practice dir.

import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

from practice.paths import REFERENCES_DIR, REPO_ROOT

PACKAGE = REPO_ROOT / "problems" / "leetcode-217"
SOLUTIONS = REPO_ROOT / "tests" / "fixtures" / "leetcode_contains_duplicate_solutions"
UPSTREAM = (
    REFERENCES_DIR / "upstream" / "neetcode-leetcode-0217-contains-duplicate-python"
)
# The MIT notice is the same upstream file as for LeetCode 1. This git blob id was
# reported by GitHub for that path, so it is an oracle that does not come from here.
UPSTREAM_LICENSE_BLOB = "144c6f237c2c9a19404bd1def098172a9fc1c7c3"


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
    started = practice(practice_dir, "attempt", "start", "leetcode", "217")
    assert started.returncode == 0, started.stderr
    attempt_id = re.search(r"Started attempt (\S+)", started.stdout)
    code = re.search(r"^Code: (.+)$", started.stdout, re.MULTILINE)
    assert attempt_id is not None and code is not None, started.stdout
    return attempt_id.group(1), Path(code.group(1))


def test_search_finds_the_problem(tmp_path: Path) -> None:
    result = practice(tmp_path, "search", "contains duplicate")
    assert result.returncode == 0, result.stderr
    assert "217" in result.stdout
    assert "contains-duplicate" in result.stdout


def test_start_copies_the_starter_byte_for_byte(tmp_path: Path) -> None:
    _, code = start(tmp_path)
    assert code.read_bytes() == (PACKAGE / "starter.py").read_bytes()


def test_the_full_flow_from_blank_to_a_passing_attempt(tmp_path: Path) -> None:
    attempt_id, code = start(tmp_path)

    blank = practice(tmp_path, "attempt", "test", attempt_id)
    assert blank.returncode == 1
    assert "STUB" in blank.stdout

    shutil.copyfile(SOLUTIONS / "ignores_last_entry.py", code)
    wrong = practice(tmp_path, "attempt", "test", attempt_id)
    assert wrong.returncode == 1
    assert "FAILED" in wrong.stdout
    assert "repeat-at-the-end" in wrong.stdout

    shutil.copyfile(SOLUTIONS / "hash_set.py", code)
    right = practice(tmp_path, "attempt", "test", attempt_id)
    assert right.returncode == 0, right.stdout
    assert "PASSED  leetcode/217: all 69 cases passed" in right.stdout

    progress = practice(tmp_path, "progress", "leetcode", "217")
    assert progress.returncode == 0, progress.stderr
    assert "passed locally" in progress.stdout
    assert "platform verdict: none recorded" in progress.stdout

    notes = practice(tmp_path, "notes", attempt_id)
    assert "stub" in notes.stdout
    assert "failed" in notes.stdout
    assert "passed" in notes.stdout


@pytest.mark.parametrize("name", ["set_length", "sort_neighbours", "dict_counts"])
def test_alternate_approaches_pass_through_the_cli(tmp_path: Path, name: str) -> None:
    attempt_id, code = start(tmp_path)
    shutil.copyfile(SOLUTIONS / f"{name}.py", code)
    result = practice(tmp_path, "attempt", "test", attempt_id)
    assert result.returncode == 0, result.stdout
    assert "PASSED" in result.stdout


def test_a_quadratic_attempt_is_reported_as_a_timeout(tmp_path: Path) -> None:
    attempt_id, code = start(tmp_path)
    shutil.copyfile(SOLUTIONS / "brute_force.py", code)
    result = practice(tmp_path, "attempt", "test", attempt_id)
    assert result.returncode == 1
    assert "PASSED" not in result.stdout
    assert "TIMEOUT" in result.stdout.upper()


def test_the_committed_references_verify_through_the_cli(tmp_path: Path) -> None:
    check = practice(tmp_path, "sources", "verify")
    assert check.returncode == 0, check.stderr
    assert re.search(r"\d+ source\(s\) verified", check.stdout)


def test_the_license_notice_is_the_upstream_blob() -> None:
    notice = UPSTREAM / "LICENSE"
    raw = subprocess.run(
        ["git", "hash-object", "--no-filters", str(notice)],
        capture_output=True,
        text=True,
        cwd=REPO_ROOT,
        timeout=60,
        check=True,
    ).stdout.strip()
    assert raw == UPSTREAM_LICENSE_BLOB


def test_the_upstream_code_is_stored_unconverted_by_git() -> None:
    code = UPSTREAM / "0217-contains-duplicate.py"
    filtered = subprocess.run(
        ["git", "hash-object", "--path", str(code.relative_to(REPO_ROOT)), str(code)],
        capture_output=True,
        text=True,
        cwd=REPO_ROOT,
        timeout=60,
        check=True,
    ).stdout.strip()
    raw = subprocess.run(
        ["git", "hash-object", "--no-filters", str(code)],
        capture_output=True,
        text=True,
        cwd=REPO_ROOT,
        timeout=60,
        check=True,
    ).stdout.strip()
    assert filtered == raw


def test_readiness_reports_ready_and_says_who_confirmed_the_facts(
    tmp_path: Path,
) -> None:
    result = practice(tmp_path, "readiness", "leetcode", "217", "--json")
    assert result.returncode == 0, result.stdout
    report = json.loads(result.stdout)
    assert report["ready"] is True
    assert [c["name"] for c in report["checks"] if not c["ok"]] == []
    assert report["platform_acceptance"] == "none"
    verified = " ".join(item["against"] for item in report["verification"]["verified"])
    assert "reported by a person, not fetched" in verified
    not_verified = " ".join(report["verification"]["not_verified"])
    assert "leetcode.com was unreachable" in not_verified
    text = practice(tmp_path, "readiness", "leetcode", "217")
    assert "READY  leetcode/217" in text.stdout
    assert "NOT READY" not in text.stdout
