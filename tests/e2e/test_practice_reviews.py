# ABOUTME: End-to-end tests for spaced reviews, run as real subprocesses over days.
# ABOUTME: A temp PRACTICE_DIR and PRACTICE_NOW drive the real Two Sum package.

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

SOLUTIONS = REPO_ROOT / "tests" / "fixtures" / "leetcode_two_sum_solutions"
SECRET = "seen = {}"


def command() -> Path:
    scripts = Path(sys.executable).parent
    return next(
        path
        for name in ("practice.exe", "practice")
        if (path := scripts / name).exists()
    )


class Learner:
    """One learner folder, run through the installed `practice` command."""

    def __init__(self, root: Path, problems: Path) -> None:
        self.root = root
        self.problems = problems
        self.day = "2026-11-01"

    def practice(self, *args: str) -> subprocess.CompletedProcess[str]:
        environment = os.environ.copy()
        environment["PRACTICE_DIR"] = str(self.root)
        environment["PRACTICE_NOW"] = f"{self.day}T09:00:00Z"
        return subprocess.run(
            [str(command()), "--problems-dir", str(self.problems), *args],
            capture_output=True,
            text=True,
            encoding="utf-8",
            timeout=120,
            check=False,
            env=environment,
        )

    def code_of(self, attempt_id: str) -> Path:
        return attempt_code_path(self.root, "leetcode", "1", attempt_id)

    def ok(self, *args: str) -> str:
        result = self.practice(*args)
        assert result.returncode == 0, result.stdout + result.stderr
        return result.stdout

    def work(self, verb: tuple[str, ...], solution: str | None) -> str:
        """Start an attempt or review, write a solution into it, and test it."""
        package = str(self.problems / "leetcode-1")
        out = self.ok(*verb, "start", "leetcode", "1", "--package", package)
        match = re.search(r"Started (?:review )?attempt (\S+)", out)
        assert match is not None
        attempt_id = match.group(1)
        if solution is not None:
            code = self.code_of(attempt_id)
            shutil.copyfile(SOLUTIONS / f"{solution}.py", code)
            self.ok("attempt", "test", attempt_id, "--package", package)
        return attempt_id


@pytest.fixture
def learner(tmp_path: Path) -> Learner:
    problems = tmp_path / "problems"
    shutil.copytree(REPO_ROOT / "problems" / "leetcode-1", problems / "leetcode-1")
    return Learner(tmp_path / "learner", problems)


def test_a_four_week_review_story_on_two_sum(learner: Learner) -> None:
    # Day 1: solve it. A one day review is scheduled from this practice date.
    learner.work(("attempt",), "hash_map")
    assert "due 2026-11-02  rung 1 of 5 (1 day gap)" in learner.ok("review", "list")

    # Day 2: due. Start a blank review; earlier code is never printed.
    learner.day = "2026-11-02"
    due = learner.ok("review", "list")
    assert "Due now:\n  leetcode 1  Two Sum" in due
    started = learner.ok(
        "review",
        "start",
        "leetcode",
        "1",
        "--package",
        str(learner.problems / "leetcode-1"),
    )
    assert "Earlier solutions are kept on disk and are not shown" in started
    assert SECRET not in started
    review_id = re.search(r"Started review attempt (\S+)", started)
    assert review_id is not None
    assert "review in progress" in learner.ok("review", "list")
    code_file = learner.code_of(review_id.group(1))
    assert SECRET not in code_file.read_text(encoding="utf-8")
    shutil.copyfile(SOLUTIONS / "hash_map.py", code_file)
    learner.ok(
        "attempt",
        "test",
        review_id.group(1),
        "--package",
        str(learner.problems / "leetcode-1"),
    )
    assert "due 2026-11-05  rung 2 of 5 (3 day gap)" in learner.ok("review", "list")

    # Day 8 (three days later): a late, hinted review shortens the gap.
    learner.day = "2026-11-09"
    hinted = learner.work(("review",), None)
    learner.ok("attempt", "note-assistance", hinted, "--kind", "hint", "--level", "1")
    code = learner.code_of(hinted)
    shutil.copyfile(SOLUTIONS / "hash_map.py", code)
    learner.ok(
        "attempt", "test", hinted, "--package", str(learner.problems / "leetcode-1")
    )
    assert "due 2026-11-10  rung 1 of 5 (1 day gap)" in learner.ok("review", "list")

    # Skip then reschedule: events are recorded, no penalty, journal is the only store.
    learner.day = "2026-11-10"
    skipped = learner.ok("review", "skip", "leetcode", "1")
    assert "No score is affected" in skipped
    assert "due 2026-11-11" in learner.ok("review", "list")
    learner.ok("review", "reschedule", "leetcode", "1", "--on", "2026-12-01")
    assert "due 2026-12-01" in learner.ok("review", "list")
    assert sorted(p.name for p in learner.root.iterdir()) == [
        "attempts",
        "journal.jsonl",
        "journal.jsonl.lock",
    ]

    for text in (learner.ok("menu", "--reviews"), learner.ok("progress")):
        assert SECRET not in text
        assert find_technique_terms(text) == []


def test_the_numbered_menu_lists_and_starts_a_due_review(learner: Learner) -> None:
    learner.work(("attempt",), "hash_map")
    learner.day = "2026-11-02"

    main_menu = learner.ok("menu")
    reviews = learner.ok("menu", "choose", "4")
    start = learner.ok("menu", "choose", "1", "--reviews")

    assert "1 review(s) due." in main_menu
    assert "4. Review problems that are due" in main_menu
    assert "Reviews due" in reviews
    assert "Start the review (1  Two Sum" in reviews
    assert "Started review attempt" in start
    for text in (main_menu, reviews, start):
        assert SECRET not in text
        assert find_technique_terms(text) == []


def test_a_bad_practice_now_fails_clearly_and_writes_nothing(learner: Learner) -> None:
    environment = os.environ.copy()
    environment["PRACTICE_DIR"] = str(learner.root)
    environment["PRACTICE_NOW"] = "not-a-time"

    result = subprocess.run(
        [str(command()), "review", "list"],
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=60,
        check=False,
        env=environment,
    )

    assert result.returncode == 2
    assert "PRACTICE_NOW" in result.stderr
    assert not learner.root.exists()
