# ABOUTME: End-to-end tests for optional timed practice, run as real subprocesses.
# ABOUTME: A temp PRACTICE_DIR, a stepping PRACTICE_NOW and the real LeetCode 1 package.

import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

from practice.history import attempt_code_path
from practice.paths import REPO_ROOT
from practice.tutor_policy import find_technique_terms

SOLUTION = (
    REPO_ROOT / "tests" / "fixtures" / "leetcode_two_sum_solutions" / "hash_map.py"
)


def command() -> Path:
    scripts = Path(sys.executable).parent
    return next(
        path
        for name in ("practice.exe", "practice")
        if (path := scripts / name).exists()
    )


class Learner:
    """One learner folder; each call runs the installed `practice` at a chosen time."""

    def __init__(self, root: Path, problems: Path) -> None:
        self.root = root
        self.problems = problems
        self.now = "2026-11-02T09:00:00Z"

    def at(self, moment: str) -> None:
        self.now = f"2026-11-{moment}:00Z"

    def practice(self, *args: str) -> subprocess.CompletedProcess[str]:
        environment = os.environ.copy()
        environment["PRACTICE_DIR"] = str(self.root)
        environment["PRACTICE_NOW"] = self.now
        return subprocess.run(
            [str(command()), "--problems-dir", str(self.problems), *args],
            capture_output=True,
            text=True,
            encoding="utf-8",
            timeout=120,
            check=False,
            env=environment,
        )

    def ok(self, *args: str) -> str:
        result = self.practice(*args)
        assert result.returncode == 0, result.stdout + result.stderr
        return result.stdout

    def start(self, *extra: str) -> str:
        package = str(self.problems / "leetcode-1")
        out = self.ok("attempt", "start", "leetcode", "1", "--package", package, *extra)
        match = re.search(r"Started attempt (\S+)", out)
        assert match is not None, out
        return match.group(1)

    def solve(self, attempt_id: str) -> None:
        code = attempt_code_path(self.root, "leetcode", "1", attempt_id)
        shutil.copyfile(SOLUTION, code)
        package = str(self.problems / "leetcode-1")
        self.ok("attempt", "test", attempt_id, "--package", package)

    def number(self, screen: list[str], label: str) -> str:
        out = self.ok("menu", *screen)
        match = re.search(rf"^\s+(\d+)\. {re.escape(label)}", out, re.MULTILINE)
        assert match is not None, out
        return match.group(1)


@pytest.fixture
def learner(tmp_path: Path) -> Learner:
    problems = tmp_path / "problems"
    shutil.copytree(REPO_ROOT / "problems" / "leetcode-1", problems / "leetcode-1")
    return Learner(tmp_path / "learner", problems)


def test_the_demo_start_timed_finish_view_time_then_start_untimed(
    learner: Learner,
) -> None:
    started = learner.ok(
        "attempt",
        "start",
        "leetcode",
        "1",
        "--package",
        str(learner.problems / "leetcode-1"),
        "--timed",
        "--limit-minutes",
        "45",
    )
    attempt_id = re.search(r"Started attempt (\S+)", started)
    assert attempt_id is not None
    timed_id = attempt_id.group(1)
    assert "timed, 45 minute limit" in started
    assert "Timer started: 2026-11-02T09:00:00.000+00:00" in started

    learner.at("02T09:10")
    midway = learner.ok("attempt", "time", timed_id)
    assert "Not finished: 10m 00s elapsed so far (35m 00s left of the limit)" in midway

    learner.at("02T09:20")
    learner.solve(timed_id)
    learner.at("02T09:30")
    explained = learner.ok(
        "attempt",
        "explain",
        timed_id,
        "--approach",
        "4",
        "--correctness",
        "4",
        "--time",
        "2",
        "--evidence",
        "walked through it",
        "--feedback",
        "clear",
    )
    learner.at("02T09:31")
    learner.ok("attempt", "finish", timed_id)

    learner.at("02T17:00")  # Hours later: a finished attempt's time does not tick.
    done = learner.ok("attempt", "time", timed_id)
    assert "First passing run: 20m" in done
    assert "after start (within the 45 minute limit)" in done
    assert "Finished: 31m 00s after start (within the 45 minute limit)" in done
    assert "separate from explanation feedback and test results" in done

    notes = learner.ok("notes", timed_id)
    assert "Timing (evidence only" in notes
    explanation_part = notes.split("Explanation assessments")[1].split("Code now")[0]
    assert "minute" not in explanation_part and "elapsed" not in explanation_part
    assert "10/10" in explained or "approach 4" in explained
    assert "elapsed" not in explained and "minute" not in explained

    learner.at("03T09:00")
    next_id = learner.start()
    fresh = learner.ok("attempt", "time", next_id)
    assert "Untimed" in fresh
    listing = learner.ok("attempt", "list")
    next_line = next(x for x in listing.splitlines() if next_id in x)
    timed_line = next(x for x in listing.splitlines() if timed_id in x)
    assert "untimed" in next_line
    assert "untimed" not in timed_line and "timed" in timed_line
    assert "Timing: untimed" in learner.ok("tutor", "start")


def test_a_limit_needs_timing_and_must_be_positive(learner: Learner) -> None:
    package = str(learner.problems / "leetcode-1")
    for extra in (["--limit-minutes", "30"], ["--timed", "--limit-minutes", "0"]):
        result = learner.practice(
            "attempt", "start", "leetcode", "1", "--package", package, *extra
        )
        assert result.returncode == 2, result.stdout + result.stderr
        assert "practice: error:" in result.stderr
    assert not (learner.root / "journal.jsonl").exists()


def test_time_on_an_attempt_that_does_not_exist_is_a_usage_error(
    learner: Learner,
) -> None:
    result = learner.practice("attempt", "time", "nope")

    assert result.returncode == 2
    assert "no attempt matches" in result.stderr


def test_the_tutor_request_names_timing_only_for_a_timed_attempt(
    learner: Learner,
) -> None:
    timed_id = learner.start("--timed", "--limit-minutes", "30")
    timed_request = learner.ok("request", timed_id, "--action", "hint")
    learner.ok("attempt", "finish", timed_id)
    plain_id = learner.start()
    plain_request = learner.ok("request", plain_id, "--action", "hint")

    assert "Timing: timed" in timed_request
    assert "30 minute limit" in timed_request
    assert "Timing: untimed" in plain_request
    assert "limit" not in plain_request.split("## Task")[0]
    assert find_technique_terms(timed_request) == []


def test_the_menu_timed_item_opts_in_for_one_attempt_only(learner: Learner) -> None:
    main = learner.ok("menu")
    assert "Timed practice" in main
    assert "Unavailable: Not available yet." in main  # Study alone remains.
    assert main.count("Not available yet.") == 1

    timed_item = learner.number([], "Timed practice")
    browse = learner.ok("menu", "choose", timed_item)
    assert "Timed practice" in browse
    assert "--browse --timed" in browse

    problem = learner.ok("menu", "choose", "1", "--browse", "--timed")
    assert "--problem leetcode 1 --timed" in problem
    assert not (learner.root / "journal.jsonl").exists()  # Choosing wrote nothing.

    timed_start = learner.number(
        ["--problem", "leetcode", "1", "--timed"], "Start a new timed practice attempt"
    )
    started = learner.ok(
        "menu", "choose", timed_start, "--problem", "leetcode", "1", "--timed"
    )
    assert "timed" in started and "untimed" not in started.split("Choose with")[0]
    timed_id = re.search(r"Started attempt (\S+)", started)
    assert timed_id is not None
    assert "Timer started" in started, (
        "starting timed from the menu records a timer like the command does"
    )

    learner.ok("attempt", "finish", timed_id.group(1))
    plain_start = learner.number(
        ["--problem", "leetcode", "1"], "Start a new practice attempt"
    )
    plain = learner.ok("menu", "choose", plain_start, "--problem", "leetcode", "1")
    assert "untimed" in plain
    assert "Timer started" not in plain
    flags = learner.ok("attempt", "list")
    assert [("untimed" in x) for x in flags.splitlines()] == [False, True]


def test_the_main_menu_never_leaves_timing_switched_on(learner: Learner) -> None:
    learner.ok("menu", "choose", learner.number([], "Timed practice"))

    main_again = learner.ok("menu")

    assert not (learner.root / "journal.jsonl").exists()
    assert "--timed" not in main_again
    started = learner.start()
    assert "untimed" in learner.ok("attempt", "list")
    assert started
