# ABOUTME: End-to-end tests for `practice menu` and `practice tui` as real subprocesses.
# ABOUTME: The numbered flow runs on Two Sum; a POSIX test drives a real pty.

import importlib
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

from practice.paths import REPO_ROOT
from practice.tutor_policy import find_technique_terms

HASH_MAP_SOLUTION = (
    REPO_ROOT / "tests" / "fixtures" / "leetcode_two_sum_solutions" / "hash_map.py"
)


def command() -> Path:
    scripts = Path(sys.executable).parent
    return next(
        path
        for name in ("practice.exe", "practice")
        if (path := scripts / name).exists()
    )


def environment(practice_dir: Path) -> dict[str, str]:
    result = os.environ.copy()
    result["PRACTICE_DIR"] = str(practice_dir)
    return result


@pytest.fixture
def learner(tmp_path: Path) -> Path:
    return tmp_path / "learner"


@pytest.fixture
def problems(tmp_path: Path) -> Path:
    root = tmp_path / "problems"
    shutil.copytree(REPO_ROOT / "problems" / "leetcode-1", root / "leetcode-1")
    return root


def practice(
    learner: Path, problems: Path, *args: str
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [str(command()), "--problems-dir", str(problems), *args],
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=120,
        check=False,
        env=environment(learner),
    )


def test_the_numbered_flow_runs_two_sum_end_to_end(
    learner: Path, problems: Path
) -> None:
    main_menu = practice(learner, problems, "menu")
    assert main_menu.returncode == 0, main_menu.stderr
    assert "1. Resume your active attempt" in main_menu.stdout
    assert "5. Get a recommendation" in main_menu.stdout
    assert "Not available yet." in main_menu.stdout  # Study and timed practice.

    browse = practice(learner, problems, "menu", "choose", "2")
    assert browse.returncode == 0, browse.stderr
    assert "1  Two Sum" in browse.stdout
    assert "practice menu choose N --browse" in browse.stdout

    problem = practice(learner, problems, "menu", "choose", "1", "--browse")
    assert problem.returncode == 0, problem.stderr
    assert "practice menu choose N --problem leetcode 1" in problem.stdout

    started = practice(
        learner, problems, "menu", "choose", "1", "--problem", "leetcode", "1"
    )
    assert started.returncode == 0, started.stderr
    match = re.search(r"Started attempt (\S+)", started.stdout)
    assert match is not None, started.stdout
    attempt_id = match.group(1)
    assert f"practice menu choose N --attempt {attempt_id}" in started.stdout

    code = learner / "attempts" / "leetcode-1" / attempt_id / "solution.py"
    blank = practice(learner, problems, "menu", "choose", "1", "--attempt", attempt_id)
    assert blank.returncode == 1  # Blank starter: tests did not pass.
    assert "Recorded this test run in the journal." in blank.stdout

    shutil.copyfile(HASH_MAP_SOLUTION, code)
    passed = practice(learner, problems, "menu", "choose", "1", "--attempt", attempt_id)
    assert passed.returncode == 0, passed.stdout + passed.stderr
    assert "PASSED" in passed.stdout

    resumed = practice(learner, problems, "menu", "choose", "1")
    assert resumed.returncode == 0, resumed.stderr
    assert attempt_id in resumed.stdout

    for text in (main_menu.stdout, browse.stdout, started.stdout, passed.stdout):
        assert find_technique_terms(text) == []


def test_a_problem_without_a_package_is_pending_and_never_started(
    learner: Path, problems: Path
) -> None:
    browse = practice(learner, problems, "menu", "--browse", "add", "two", "numbers")
    assert browse.returncode == 0, browse.stderr
    assert "Pending" in browse.stdout

    problem = practice(learner, problems, "menu", "--problem", "leetcode", "2")
    assert "Pending" in problem.stdout
    start = practice(
        learner, problems, "menu", "choose", "1", "--problem", "leetcode", "2"
    )
    assert start.returncode == 1
    assert "Nothing was done." in start.stdout
    assert not (learner / "journal.jsonl").exists()


def test_unavailable_future_items_do_nothing(learner: Path, problems: Path) -> None:
    result = practice(learner, problems, "menu", "choose", "6")

    assert result.returncode == 1
    assert "Not available yet." in result.stdout
    assert "Nothing was done." in result.stdout
    assert not (learner / "journal.jsonl").exists()


def test_search_accepts_several_unquoted_words(learner: Path, problems: Path) -> None:
    result = practice(learner, problems, "search", "sum", "of")

    assert result.returncode == 0, result.stderr
    assert "sum" in result.stdout.lower()


def test_the_terminal_menu_without_a_terminal_points_to_the_numbered_menu(
    learner: Path, problems: Path
) -> None:
    result = practice(learner, problems, "tui")

    assert result.returncode == 2
    assert "needs a terminal" in result.stderr
    assert "practice menu" in result.stderr


@pytest.mark.skipif(sys.platform == "win32", reason="needs a POSIX pseudo-terminal")
def test_the_terminal_menu_runs_in_a_real_pseudo_terminal(
    learner: Path, problems: Path
) -> None:
    import select
    import time

    pty = importlib.import_module("pty")  # POSIX only, so imported on demand.
    master, slave = pty.openpty()
    process = subprocess.Popen(
        [str(command()), "--problems-dir", str(problems), "tui"],
        stdin=slave,
        stdout=slave,
        stderr=slave,
        env=environment(learner),
        close_fds=True,
    )
    os.close(slave)
    output = b""
    deadline = time.monotonic() + 60
    for keys in (b"2\r", b"1\r", b"1\r", b"\x03"):
        time.sleep(1.5)
        os.write(master, keys)
    while time.monotonic() < deadline and process.poll() is None:
        ready, _, _ = select.select([master], [], [], 0.5)
        if ready:
            try:
                output += os.read(master, 65536)
            except OSError:
                break
    process.wait(timeout=30)
    os.close(master)

    assert process.returncode == 0
    assert b"Started attempt" in output
    assert (learner / "journal.jsonl").exists()
