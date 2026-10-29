# ABOUTME: End-to-end tests for `practice request`, run as a real subprocess.
# ABOUTME: A temp PRACTICE_DIR and the committed LeetCode 1 package; no mocks anywhere.

import os
import re
import subprocess
import sys
from pathlib import Path

import pytest

from practice.paths import REPO_ROOT
from practice.tutor_policy import find_technique_terms

PACKAGE = REPO_ROOT / "problems" / "leetcode-1"


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


def start(practice_dir: Path) -> str:
    started = practice(practice_dir, "attempt", "start", "leetcode", "1", "--timed")
    assert started.returncode == 0, started.stderr
    match = re.search(r"Started attempt (\S+)", started.stdout)
    assert match is not None, started.stdout
    return match.group(1)


def journal(practice_dir: Path) -> bytes:
    return (practice_dir / "journal.jsonl").read_bytes()


def test_hint_request_demo_prints_and_saves_a_permitted_block(tmp_path: Path) -> None:
    attempt_id = start(tmp_path)
    before = journal(tmp_path)

    result = practice(tmp_path, "request", attempt_id, "--action", "hint")

    assert result.returncode == 0, result.stderr
    saved = tmp_path / "requests" / f"{attempt_id}-1-hint.md"
    assert saved.is_file()
    assert saved.read_text(encoding="utf-8") == result.stdout
    assert str(saved) in result.stderr
    text = result.stdout
    assert "Platform: leetcode" in text
    assert "Problem: 1  Two Sum" in text
    assert f"Attempt: {attempt_id}" in text
    assert "Mode: practice" in text
    assert "Timing: untimed" in text  # The attempt was timed; the request is not.
    assert "Action: hint" in text
    assert "hint level 0 only" in text
    assert "do not name the technique" in text
    assert find_technique_terms(text) == []
    for withheld in ("notes.md", "hints/1.md", "hints/2.md", "hints/3.md"):
        assert withheld not in text
    assert journal(tmp_path) == before
    assert "assistance" not in before.decode("utf-8")


def test_timed_and_study_are_per_request_choices(tmp_path: Path) -> None:
    attempt_id = start(tmp_path)
    result = practice(
        tmp_path,
        "request",
        attempt_id,
        "--action",
        "concept-refresher",
        "--mode",
        "study",
        "--timed",
    )
    assert result.returncode == 0, result.stderr
    assert "Mode: study" in result.stdout
    assert "Timing: timed" in result.stdout
    follow_up = practice(
        tmp_path, "request", attempt_id, "--action", "concept-refresher"
    )
    assert "Mode: practice" in follow_up.stdout
    assert "Timing: untimed" in follow_up.stdout


def test_hint_levels_follow_recorded_help_and_explicit_reveal(tmp_path: Path) -> None:
    attempt_id = start(tmp_path)
    noted = practice(
        tmp_path,
        "attempt",
        "note-assistance",
        attempt_id,
        "--kind",
        "hint",
        "--level",
        "0",
    )
    assert noted.returncode == 0, noted.stderr
    default = practice(tmp_path, "request", attempt_id, "--action", "hint")
    assert "hint level 1 only" in default.stdout
    explicit = practice(
        tmp_path, "request", attempt_id, "--action", "hint", "--reveal", "3"
    )
    assert "hint level 3 only" in explicit.stdout
    assert "may name the technique" in explicit.stdout


def test_explain_solution_needs_the_explicit_reveal(tmp_path: Path) -> None:
    attempt_id = start(tmp_path)
    refused = practice(tmp_path, "request", attempt_id, "--action", "explain-solution")
    assert refused.returncode != 0
    assert "--reveal solution" in refused.stderr
    assert refused.stdout == ""
    assert not (tmp_path / "requests").exists()

    allowed = practice(
        tmp_path,
        "request",
        attempt_id,
        "--action",
        "explain-solution",
        "--reveal",
        "solution",
    )
    assert allowed.returncode == 0, allowed.stderr
    assert "notes.md" in allowed.stdout
    assert "--kind reveal" in allowed.stdout


@pytest.mark.parametrize(
    "action", ["review-my-code", "explain-my-approach", "stuck", "concept-refresher"]
)
def test_every_other_action_prepares_a_request_without_touching_the_journal(
    tmp_path: Path, action: str
) -> None:
    attempt_id = start(tmp_path)
    before = journal(tmp_path)
    result = practice(tmp_path, "request", attempt_id, "--action", action)
    assert result.returncode == 0, result.stderr
    assert f"Action: {action}" in result.stdout
    assert find_technique_terms(result.stdout) == []
    assert journal(tmp_path) == before


def test_unavailable_cases_fail_with_a_nonzero_exit_and_a_clear_error(
    tmp_path: Path,
) -> None:
    attempt_id = start(tmp_path)
    cases = [
        (("request", "no-such-attempt", "--action", "hint"), "no attempt matches"),
        (("request", attempt_id, "--action", "hint", "--reveal", "9"), "level 9"),
        (("request", attempt_id, "--action", "stuck", "--reveal", "1"), "--reveal"),
    ]
    for args, message in cases:
        result = practice(tmp_path, *args)
        assert result.returncode != 0, args
        assert message in result.stderr, (args, result.stderr)
        assert result.stdout == ""

    unsupported = practice(tmp_path, "request", attempt_id, "--action", "solve-it")
    assert unsupported.returncode != 0
    assert not (tmp_path / "requests").exists()

    finished = practice(tmp_path, "attempt", "finish", attempt_id)
    assert finished.returncode == 0, finished.stderr
    after_finish = practice(tmp_path, "request", attempt_id, "--action", "hint")
    assert after_finish.returncode != 0
    assert "finished" in after_finish.stderr
    assert not (tmp_path / "requests").exists()


def test_a_pending_exercise_fails_clearly(tmp_path: Path) -> None:
    attempt_id = start(tmp_path)
    pending = tmp_path / "pending-package"
    pending.mkdir()
    (pending / "problem.json").write_text(
        '{"platform": "leetcode", "id": "1", "title": "Two Sum", '
        '"language": "python", "callable": {"adapter": "function", '
        '"name": "twoSum", "parameters": ["nums", "target"]}}',
        encoding="utf-8",
    )
    result = practice(
        tmp_path, "request", attempt_id, "--action", "hint", "--package", str(pending)
    )
    assert result.returncode != 0
    assert "not ready" in result.stderr


def test_the_requests_directory_is_ignored_by_the_repository() -> None:
    result = subprocess.run(
        [
            "git",
            "-C",
            str(REPO_ROOT),
            "check-ignore",
            "-v",
            "--no-index",
            "--",
            ".practice/requests/A-1-hint.md",
        ],
        capture_output=True,
        text=True,
        check=False,
        timeout=60,
    )
    assert result.returncode == 0, result.stderr
    assert result.stdout.split("	", 1)[0].split(":", 1)[0].endswith(".gitignore")
