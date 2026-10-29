# ABOUTME: End-to-end tests for `practice recommend`, run as real subprocesses.
# ABOUTME: A temp PRACTICE_DIR and PRACTICE_NOW drive real packages and a real journal.

import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest

from practice.paths import REPO_ROOT
from practice.tutor_policy import find_technique_terms

FIXTURES = REPO_ROOT / "tests" / "fixtures"
SOLUTIONS = {
    "1": FIXTURES / "leetcode_two_sum_solutions" / "hash_map.py",
    "217": FIXTURES / "leetcode_contains_duplicate_solutions" / "hash_set.py",
}
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

    def ok(self, *args: str) -> str:
        result = self.practice(*args)
        assert result.returncode == 0, result.stdout + result.stderr
        return result.stdout

    def recommend(self, *args: str) -> str:
        return self.ok("recommend", *args)

    def pick(self) -> dict[str, Any]:
        data: dict[str, Any] = json.loads(self.recommend("--json"))
        return data

    def start(self, problem: str, verb: str = "attempt") -> str:
        package = str(self.problems / f"leetcode-{problem}")
        out = self.ok(verb, "start", "leetcode", problem, "--package", package)
        match = re.search(r"Started (?:review )?attempt (\S+)", out)
        assert match is not None, out
        return match.group(1)

    def code_of(self, problem: str, attempt_id: str) -> Path:
        from practice.history import attempt_code_path

        return attempt_code_path(self.root, "leetcode", problem, attempt_id)

    def test(self, problem: str, attempt_id: str) -> None:
        shutil.copyfile(SOLUTIONS[problem], self.code_of(problem, attempt_id))
        package = str(self.problems / f"leetcode-{problem}")
        self.ok("attempt", "test", attempt_id, "--package", package)

    def solve(self, problem: str, verb: str = "attempt") -> str:
        attempt_id = self.start(problem, verb)
        self.test(problem, attempt_id)
        return attempt_id

    def explain(self, attempt_id: str, approach: int, why: int, time: int) -> None:
        self.ok(
            "attempt",
            "explain",
            attempt_id,
            "--approach",
            str(approach),
            "--correctness",
            str(why),
            "--time",
            str(time),
            "--evidence",
            "said it aloud",
            "--feedback",
            "ok",
        )

    def journal(self) -> bytes:
        path = self.root / "journal.jsonl"
        return path.read_bytes() if path.exists() else b""


def make_learner(tmp_path: Path, *problems: str) -> Learner:
    folder = tmp_path / "problems"
    folder.mkdir()
    for problem in problems:
        shutil.copytree(
            REPO_ROOT / "problems" / f"leetcode-{problem}",
            folder / f"leetcode-{problem}",
        )
    return Learner(tmp_path / "learner", folder)


@pytest.fixture
def learner(tmp_path: Path) -> Learner:
    return make_learner(tmp_path, "1", "217")


def assert_clean(text: str) -> None:
    assert SECRET not in text
    assert find_technique_terms(text) == []
    assert "concept" not in text.lower().replace("concept explanation", "")


def test_a_brand_new_learner_gets_the_first_objective(learner: Learner) -> None:
    text = learner.recommend()
    pick = learner.pick()

    assert "Recommended next:" in text
    assert "1  Two Sum [easy]" in text
    assert "Why: next curriculum objective. It is part of Objective 1." in text
    assert "Evidence: No attempts yet." in text
    assert "To start it: practice attempt start leetcode 1" in text
    assert pick["primary"]["reason"] == "next_objective"
    assert pick["primary"]["label"] == "Two Sum [easy]"
    assert_clean(text)


def test_recommend_starts_nothing_and_writes_nothing(learner: Learner) -> None:
    learner.solve("1")
    before = learner.journal()
    listing_before = sorted(p.name for p in learner.root.iterdir())

    learner.recommend()
    learner.recommend("--json")
    learner.recommend("--choose", "1")

    assert learner.journal() == before
    assert sorted(p.name for p in learner.root.iterdir()) == listing_before


def test_a_brand_new_learner_has_no_state_created(learner: Learner) -> None:
    learner.recommend()

    assert not learner.root.exists() or not (learner.root / "journal.jsonl").exists()


def test_one_independent_pass_is_not_mastery(learner: Learner) -> None:
    learner.solve("1")

    pick = learner.pick()
    text = learner.recommend()

    assert pick["primary"]["problem_id"] == "217"
    assert pick["primary"]["reason"] == "next_objective"
    assert not any(
        c["problem_id"] == "1" and c["evidence"]["mastered"]
        for c in [pick["primary"], *pick["alternatives"]]
    )
    learner.day = "2026-11-02"
    due = learner.pick()["primary"]
    assert due["problem_id"] == "1"
    assert due["evidence"]["status"] == "independent"
    assert due["evidence"]["mastered"] is False
    assert "Not yet mastered" in due["evidence"]["text"]
    assert_clean(text)


def test_a_well_explained_independent_pass_is_mastered(learner: Learner) -> None:
    attempt = learner.solve("1")
    learner.explain(attempt, 4, 4, 2)
    learner.day = "2026-11-02"

    evidence = learner.pick()["primary"]["evidence"]

    assert evidence["status"] == "mastered"
    assert evidence["explanation"] == "ok"
    assert "Mastered" in evidence["text"]


def test_a_low_explanation_keeps_an_independent_pass_unmastered(
    learner: Learner,
) -> None:
    attempt = learner.solve("1")
    learner.explain(attempt, 1, 1, 0)
    learner.day = "2026-11-02"

    evidence = learner.pick()["primary"]["evidence"]

    assert evidence["status"] == "independent"
    assert evidence["explanation"] == "low"
    assert "explanation scored low" in evidence["text"]


def test_a_pass_with_heavy_help_is_not_independent(learner: Learner) -> None:
    attempt = learner.start("1")
    for level in ("1", "2", "3"):
        learner.ok(
            "attempt", "note-assistance", attempt, "--kind", "hint", "--level", level
        )
    learner.ok("attempt", "note-assistance", attempt, "--kind", "reveal")
    learner.test("1", attempt)

    primary = learner.pick()["primary"]
    text = learner.recommend()

    assert primary["problem_id"] == "1"
    assert primary["reason"] == "next_objective"
    assert primary["evidence"]["status"] == "passed_with_help"
    assert primary["evidence"]["independent"] is False
    assert "Passed with help (3 hints, 1 reveal)" in text
    assert_clean(text)


def test_a_due_review_beats_the_next_objective(learner: Learner) -> None:
    learner.solve("1")
    learner.day = "2026-11-02"

    pick = learner.pick()
    text = learner.recommend()

    assert pick["primary"]["problem_id"] == "1"
    assert pick["primary"]["reason"] == "due_review"
    assert pick["primary"]["action"] == "review"
    assert pick["primary"]["command"] == "practice review start leetcode 1"
    assert "Why: due review. A blank review was due on 2026-11-02." in text
    assert [c["problem_id"] for c in pick["alternatives"]] == ["217"]
    assert pick["alternatives"][0]["reason"] == "next_objective"


def test_a_prerequisite_gap_beats_the_next_objective(learner: Learner) -> None:
    attempt = learner.start("217")
    learner.ok("attempt", "finish", attempt)

    pick = learner.pick()
    text = learner.recommend()

    assert pick["primary"]["problem_id"] == "1"
    assert pick["primary"]["reason"] == "prerequisite_gap"
    assert pick["primary"]["reason_text"] == "prerequisite gap"
    assert "builds up to a problem you have already tried" in text
    assert_clean(text)


def test_an_unfinished_attempt_is_resumed_first(learner: Learner) -> None:
    learner.solve("1")
    learner.day = "2026-11-02"
    attempt = learner.start("217")

    pick = learner.pick()

    assert pick["primary"]["problem_id"] == "217"
    assert pick["primary"]["reason"] == "resume"
    assert pick["primary"]["action"] == "resume"
    assert pick["primary"]["attempt_id"] == attempt
    assert pick["primary"]["command"] == "practice attempt resume leetcode 217"
    assert pick["alternatives"][0]["reason"] == "due_review"


def test_with_nothing_left_it_says_so_and_exits_zero(learner: Learner) -> None:
    learner.solve("1")
    learner.solve("217")
    learner.ok("review", "reschedule", "leetcode", "1", "--on", "2027-01-01")
    learner.ok("review", "reschedule", "leetcode", "217", "--on", "2027-01-01")
    learner.day = "2026-11-02"

    result = learner.practice("recommend")
    pick = learner.pick()

    assert result.returncode == 0
    assert "Nothing to recommend" in result.stdout
    assert "no ready exercise yet" in result.stdout
    assert pick["primary"] is None
    assert pick["alternatives"] == []
    assert pick["message"] in result.stdout


def test_a_problem_without_a_ready_package_is_never_recommended(
    tmp_path: Path,
) -> None:
    learner = make_learner(tmp_path, "1")

    pick = learner.pick()
    everything = [pick["primary"], *pick["alternatives"]]

    assert [c["problem_id"] for c in everything] == ["1"]
    assert pick["pending"] >= 1
    assert "waiting for ready exercises" in learner.recommend()


def test_nothing_is_recommended_when_no_package_is_ready(tmp_path: Path) -> None:
    learner = make_learner(tmp_path)

    result = learner.practice("recommend")

    assert result.returncode == 0
    assert "Nothing to recommend right now" in result.stdout


def test_repeated_runs_are_identical(learner: Learner) -> None:
    learner.solve("1")
    learner.day = "2026-11-02"

    runs = {learner.recommend() for _ in range(3)}
    json_runs = {learner.recommend("--json") for _ in range(3)}

    assert len(runs) == 1
    assert len(json_runs) == 1


def test_choose_shows_one_pick_and_starts_nothing(learner: Learner) -> None:
    learner.solve("1")
    learner.day = "2026-11-02"
    before = learner.journal()

    second = learner.recommend("--choose", "2")
    as_json = json.loads(learner.recommend("--choose", "2", "--json"))
    out_of_range = learner.practice("recommend", "--choose", "9")

    assert "You chose:" in second
    assert "217" in second
    assert "Nothing was started or recorded" in second
    assert as_json["problem_id"] == "217"
    assert out_of_range.returncode != 0
    assert "choose a number from 1 to 2" in out_of_range.stderr
    assert learner.journal() == before


def test_a_bad_practice_now_fails_clearly(learner: Learner) -> None:
    environment = os.environ.copy()
    environment["PRACTICE_DIR"] = str(learner.root)
    environment["PRACTICE_NOW"] = "not-a-time"

    result = subprocess.run(
        [str(command()), "recommend"],
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=60,
        check=False,
        env=environment,
    )

    assert result.returncode != 0
    assert "PRACTICE_NOW" in result.stderr
    assert not (learner.root / "journal.jsonl").exists()


def test_the_numbered_menu_shows_and_starts_the_recommendation(
    learner: Learner,
) -> None:
    main_menu = learner.ok("menu")
    shown = learner.ok("menu", "--recommend")
    started = learner.ok("menu", "choose", "1", "--recommend")

    assert "5. Get a recommendation for what to practice next" in main_menu
    assert "6. Study a concept" in main_menu
    assert "Two Sum [easy]" in shown
    assert "next curriculum objective" in shown
    assert "Started attempt" in started
    for text in (main_menu, shown, started):
        assert SECRET not in text
        assert find_technique_terms(text) == []
