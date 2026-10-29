# ABOUTME: End-to-end tests that record explanation assessments through the CLI.
# ABOUTME: Real subprocesses, a temp PRACTICE_DIR and real files; no mocks anywhere.

import json
import os
import re
import shutil
import subprocess
import sys
from collections.abc import Callable
from pathlib import Path

import pytest

Solution = Callable[[str], Path]


class Learner:
    """A learner directory driven only through the practice command."""

    def __init__(self, practice_dir: Path, package: Path) -> None:
        self.practice_dir = practice_dir
        self.package = package

    def practice(self, *args: str) -> subprocess.CompletedProcess[str]:
        scripts = Path(sys.executable).parent
        command = next(
            path
            for name in ("practice.exe", "practice")
            if (path := scripts / name).exists()
        )
        environment = dict(os.environ, PRACTICE_DIR=str(self.practice_dir))
        return subprocess.run(
            [str(command), *args],
            capture_output=True,
            text=True,
            encoding="utf-8",
            timeout=120,
            check=False,
            env=environment,
        )

    def start(self) -> str:
        result = self.practice(
            "attempt", "start", "leetcode", "1", "--package", str(self.package)
        )
        assert result.returncode == 0, result.stdout + result.stderr
        match = re.search(r"Started attempt (\S+)", result.stdout)
        assert match is not None, result.stdout
        return match.group(1)

    def code_path(self, attempt_id: str) -> Path:
        return (
            self.practice_dir / "attempts" / "leetcode-1" / attempt_id / "solution.py"
        )

    def solve(self, attempt_id: str, solution: Path) -> None:
        shutil.copyfile(solution, self.code_path(attempt_id))
        result = self.practice(
            "attempt", "test", attempt_id, "--package", str(self.package)
        )
        assert result.returncode == 0, result.stdout + result.stderr

    def explain(self, attempt_id: str, *flags: str) -> subprocess.CompletedProcess[str]:
        return self.practice(
            "attempt",
            "explain",
            attempt_id,
            *flags,
            "--evidence",
            "Walked through the loop and the invariant.",
            "--feedback",
            "Accurate and clear.",
        )

    def journal(self) -> list[dict[str, object]]:
        text = (self.practice_dir / "journal.jsonl").read_text(encoding="utf-8")
        return [json.loads(line) for line in text.splitlines()]


@pytest.fixture
def learner(tmp_path: Path, leetcode_two_sum_package: Path) -> Learner:
    return Learner(tmp_path / "learner", leetcode_two_sum_package)


def test_slow_correct_solution_earns_full_core_and_a_separate_bonus(
    learner: Learner, two_sum_solution: Solution
) -> None:
    attempt_id = learner.start()
    learner.solve(attempt_id, two_sum_solution("correct_brute_force"))

    result = learner.practice(
        "attempt",
        "explain",
        attempt_id,
        "--approach",
        "4",
        "--correctness",
        "4",
        "--time",
        "2",
        "--space",
        "1",
        "--evidence",
        "Checked every pair; O(n^2) time, O(1) extra space.",
        "--feedback",
        "Accurate for the code you wrote.",
        "--coaching",
        "What work repeats across the inner loops?",
    )

    assert result.returncode == 0, result.stdout + result.stderr
    assert "10/10 +1 bonus" in result.stdout
    assert "initial" in result.stdout
    notes = learner.practice("notes", attempt_id).stdout
    assert "Explanation assessments" in notes
    assert "10/10 +1 bonus" in notes
    assert "current" in notes
    assert "Checked every pair; O(n^2) time, O(1) extra space." in notes
    assert "Accurate for the code you wrote." in notes
    assert "optimization coaching (not scored): What work repeats" in notes
    progress = learner.practice("progress").stdout
    assert "explanation: 10/10 +1 bonus" in progress
    assert "passed locally" in progress  # Completion is untouched.


def test_missing_space_analysis_is_not_a_penalty_and_not_a_zero(
    learner: Learner, two_sum_solution: Solution
) -> None:
    attempt_id = learner.start()
    learner.solve(attempt_id, two_sum_solution("correct_hash_map"))

    result = learner.explain(
        attempt_id, "--approach", "4", "--correctness", "4", "--time", "2"
    )

    assert result.returncode == 0, result.stdout + result.stderr
    assert "10/10" in result.stdout
    assert "bonus" not in result.stdout
    assert learner.journal()[-1]["space_complexity"] is None


def test_revisions_are_kept_and_shown_in_order(
    learner: Learner, two_sum_solution: Solution
) -> None:
    attempt_id = learner.start()
    learner.solve(attempt_id, two_sum_solution("correct_hash_map"))
    learner.explain(attempt_id, "--approach", "2", "--time", "1")
    learner.explain(attempt_id, "--approach", "4", "--correctness", "4", "--time", "2")

    notes = learner.practice("notes", attempt_id).stdout

    assert "initial" in notes
    assert "revision 1" in notes
    assert notes.index("partial 3/6") < notes.index("10/10")
    kinds = [e["type"] for e in learner.journal()]
    assert kinds.count("explanation_assessment") == 2
    progress = learner.practice("progress").stdout
    assert "explanation: 10/10 (revision 1, current)" in progress


def test_editing_the_code_marks_the_assessment_stale(
    learner: Learner, two_sum_solution: Solution
) -> None:
    attempt_id = learner.start()
    learner.solve(attempt_id, two_sum_solution("correct_hash_map"))
    learner.explain(attempt_id, "--approach", "4", "--correctness", "4", "--time", "2")
    code = learner.code_path(attempt_id)

    code.write_text(code.read_text(encoding="utf-8") + "\n# tweak\n", encoding="utf-8")

    progress = learner.practice("progress").stdout
    assert "explanation: 10/10 (initial, stale after edit)" in progress
    assert "stale after edit" in learner.practice("notes", attempt_id).stdout


def test_no_assessment_reads_as_not_assessed(
    learner: Learner, two_sum_solution: Solution
) -> None:
    attempt_id = learner.start()
    learner.solve(attempt_id, two_sum_solution("correct_hash_map"))

    assert "explanation: not assessed" in learner.practice("progress").stdout
    assert "No explanation assessed" in learner.practice("notes", attempt_id).stdout


def test_explicit_ungraded_is_recorded_and_is_not_zero(
    learner: Learner, two_sum_solution: Solution
) -> None:
    attempt_id = learner.start()
    learner.solve(attempt_id, two_sum_solution("correct_hash_map"))

    result = learner.explain(attempt_id, "--ungraded")

    assert result.returncode == 0, result.stdout + result.stderr
    event = learner.journal()[-1]
    assert event["approach"] is None and event["correctness"] is None
    assert "explanation: not assessed" in learner.practice("progress").stdout
    assert "0/10" not in learner.practice("progress").stdout


def test_recording_without_a_passing_run_is_allowed_but_labelled(
    learner: Learner,
) -> None:
    attempt_id = learner.start()

    result = learner.explain(attempt_id, "--approach", "3")

    assert result.returncode == 0, result.stdout + result.stderr
    assert "no passing local run" in result.stdout
    assert "no passing local run" in learner.practice("notes", attempt_id).stdout
    assert "in progress" in learner.practice("progress").stdout


@pytest.mark.parametrize(
    "flags",
    [
        ("--approach", "5"),
        ("--correctness", "-1"),
        ("--time", "3"),
        ("--space", "2"),
        (),
        ("--ungraded", "--approach", "1"),
    ],
)
def test_invalid_input_exits_2_with_a_clear_error_and_writes_nothing(
    learner: Learner, flags: tuple[str, ...]
) -> None:
    attempt_id = learner.start()
    before = learner.journal()

    result = learner.explain(attempt_id, *flags)

    assert result.returncode == 2, result.stdout + result.stderr
    assert "practice: error:" in result.stderr or "usage:" in result.stderr
    assert learner.journal() == before


def test_out_of_range_error_names_the_component_and_range(learner: Learner) -> None:
    attempt_id = learner.start()

    result = learner.explain(attempt_id, "--approach", "5")

    assert "approach" in result.stderr
    assert "0 to 4" in result.stderr


def test_unknown_attempt_exits_2(learner: Learner) -> None:
    result = learner.explain("nope", "--approach", "1")

    assert result.returncode == 2
    assert "no attempt matches" in result.stderr


def test_practice_dir_flag_wins_over_the_environment(
    learner: Learner, tmp_path: Path, two_sum_solution: Solution
) -> None:
    attempt_id = learner.start()
    elsewhere = tmp_path / "elsewhere"

    result = subprocess.run(
        [
            str(
                next(
                    p
                    for n in ("practice.exe", "practice")
                    if (p := Path(sys.executable).parent / n).exists()
                )
            ),
            "--practice-dir",
            str(learner.practice_dir),
            "attempt",
            "explain",
            attempt_id,
            "--approach",
            "1",
            "--evidence",
            "e",
            "--feedback",
            "f",
        ],
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=False,
        env=dict(os.environ, PRACTICE_DIR=str(elsewhere)),
    )

    assert result.returncode == 0, result.stdout + result.stderr
    assert not elsewhere.exists()
