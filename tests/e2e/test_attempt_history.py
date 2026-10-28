# ABOUTME: End-to-end tests that drive attempt and progress commands in subprocesses.
# ABOUTME: Includes the demo: start, quit, resume, test, edit, then see a stale pass.

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
REPO_ROOT = Path(__file__).resolve().parents[2]


class Learner:
    """One learner directory plus the exercise package, driven through the CLI."""

    def __init__(self, practice_dir: Path, package: Path) -> None:
        self.practice_dir = practice_dir
        self.package = package

    def practice(
        self, *args: str, env: dict[str, str] | None = None
    ) -> subprocess.CompletedProcess[str]:
        scripts = Path(sys.executable).parent
        command = next(
            path
            for name in ("practice.exe", "practice")
            if (path := scripts / name).exists()
        )
        environment = {k: v for k, v in os.environ.items() if k != "PRACTICE_DIR"}
        environment.update(env or {})
        return subprocess.run(
            [str(command), "--practice-dir", str(self.practice_dir), *args],
            capture_output=True,
            text=True,
            encoding="utf-8",
            timeout=120,
            check=False,
            env=environment,
        )

    def start(self, *extra: str) -> str:
        result = self.practice(
            "attempt", "start", "leetcode", "1", "--package", str(self.package), *extra
        )
        assert result.returncode == 0, result.stdout + result.stderr
        match = re.search(r"Started attempt (\S+)", result.stdout)
        assert match is not None, result.stdout
        return match.group(1)

    def code_path(self, attempt_id: str) -> Path:
        return (
            self.practice_dir / "attempts" / "leetcode-1" / attempt_id / "solution.py"
        )

    def test(self, attempt_id: str) -> subprocess.CompletedProcess[str]:
        return self.practice(
            "attempt", "test", attempt_id, "--package", str(self.package)
        )

    def journal_lines(self) -> list[str]:
        text = (self.practice_dir / "journal.jsonl").read_text(encoding="utf-8")
        return text.splitlines()


@pytest.fixture
def learner(tmp_path: Path, leetcode_two_sum_package: Path) -> Learner:
    return Learner(tmp_path / "learner", leetcode_two_sum_package)


def test_demo_start_quit_resume_test_edit_and_see_the_pass_go_stale(
    learner: Learner, two_sum_solution: Solution
) -> None:
    attempt_id = learner.start()
    code = learner.code_path(attempt_id)
    assert "def two_sum(nums, target):" in code.read_text(encoding="utf-8")

    # Quit mid-session: no goodbye command exists. A later process resumes it.
    resumed = learner.practice("attempt", "resume")
    assert resumed.returncode == 0, resumed.stdout + resumed.stderr
    assert attempt_id in resumed.stdout
    assert "in progress" in resumed.stdout
    assert str(code) in resumed.stdout

    shutil.copyfile(two_sum_solution("correct_hash_map"), code)
    tested = learner.test(attempt_id)
    assert tested.returncode == 0, tested.stdout + tested.stderr
    assert tested.stdout.startswith("PASSED")
    progress = learner.practice("progress")
    assert "passed locally" in progress.stdout

    code.write_text(code.read_text(encoding="utf-8") + "\n# tweak\n", encoding="utf-8")
    stale = learner.practice("progress")
    assert "stale after edit" in stale.stdout
    assert "passed locally" not in stale.stdout
    assert "stale after edit" in learner.practice("attempt", "resume").stdout

    # The earlier pass is still in the journal.
    events = [json.loads(line) for line in learner.journal_lines()]
    assert [e["type"] for e in events] == ["attempt_started", "test_run"]
    assert events[1]["status"] == "passed"


def test_resume_picks_the_most_recent_unfinished_attempt(learner: Learner) -> None:
    first = learner.start()
    second = learner.start()
    assert learner.practice("attempt", "finish", second).returncode == 0

    result = learner.practice("attempt", "resume", "leetcode", "1")

    assert result.returncode == 0, result.stdout + result.stderr
    assert first in result.stdout
    assert second not in result.stdout


def test_resume_with_nothing_unfinished_says_so(learner: Learner) -> None:
    result = learner.practice("attempt", "resume")

    assert result.returncode == 1
    assert "No unfinished attempt" in result.stdout


def test_resume_and_list_never_print_earlier_solution_code(
    learner: Learner, two_sum_solution: Solution
) -> None:
    first = learner.start()
    shutil.copyfile(two_sum_solution("correct_hash_map"), learner.code_path(first))
    secret = "seen = {}"
    assert secret in learner.code_path(first).read_text(encoding="utf-8")

    learner.start()
    outputs = [
        learner.practice("attempt", "resume"),
        learner.practice("attempt", "list"),
        learner.practice("progress"),
        learner.practice("notes", first),
    ]

    for output in outputs:
        assert output.returncode == 0, output.stdout + output.stderr
        assert secret not in output.stdout


def test_blank_review_attempt_preserves_the_earlier_code(
    learner: Learner, two_sum_solution: Solution
) -> None:
    first = learner.start()
    shutil.copyfile(two_sum_solution("correct_hash_map"), learner.code_path(first))
    before = learner.code_path(first).read_bytes()

    second = learner.start()

    assert second != first
    assert learner.code_path(first).read_bytes() == before
    assert "seen" not in learner.code_path(second).read_text(encoding="utf-8")


def test_timing_is_opt_in_per_attempt(learner: Learner) -> None:
    timed = learner.start("--timed", "--mode", "study")
    untimed = learner.start()

    listing = learner.practice("attempt", "list").stdout

    timed_line = next(line for line in listing.splitlines() if timed in line)
    untimed_line = next(line for line in listing.splitlines() if untimed in line)
    assert "study" in timed_line
    assert "timed" in timed_line
    assert "untimed" in untimed_line


def test_failed_test_run_is_recorded_and_exits_1(
    learner: Learner, two_sum_solution: Solution
) -> None:
    attempt_id = learner.start()
    shutil.copyfile(two_sum_solution("wrong_answer"), learner.code_path(attempt_id))

    result = learner.test(attempt_id)

    assert result.returncode == 1
    assert result.stdout.startswith("FAILED")
    last = json.loads(learner.journal_lines()[-1])
    assert last["type"] == "test_run"
    assert last["status"] == "failed"
    assert "in progress" in learner.practice("progress").stdout


def test_assistance_and_verdict_are_recorded_and_shown_in_derived_views(
    learner: Learner, two_sum_solution: Solution
) -> None:
    attempt_id = learner.start()
    shutil.copyfile(two_sum_solution("correct_hash_map"), learner.code_path(attempt_id))
    learner.test(attempt_id)

    hint = learner.practice(
        "attempt",
        "note-assistance",
        attempt_id,
        "--kind",
        "hint",
        "--level",
        "1",
        "--summary",
        "asked what a lookup could remember",
    )
    verdict = learner.practice(
        "attempt",
        "verdict",
        attempt_id,
        "--status",
        "accepted",
        "--source",
        "LeetCode submissions page",
        "--date",
        "2026-10-28",
    )

    assert hint.returncode == 0, hint.stdout + hint.stderr
    assert verdict.returncode == 0, verdict.stdout + verdict.stderr
    progress = learner.practice("progress").stdout
    assert "passed locally" in progress
    assert "accepted" in progress
    assert "LeetCode submissions page" in progress
    notes = learner.practice("notes", attempt_id).stdout
    assert "hint level 1" in notes
    assert "asked what a lookup could remember" in notes
    assert "platform verdict: accepted" in notes


def test_verdict_alone_never_creates_a_local_pass(learner: Learner) -> None:
    attempt_id = learner.start()

    learner.practice(
        "attempt", "verdict", attempt_id, "--status", "accepted", "--source", "memo"
    )

    progress = learner.practice("progress").stdout
    assert "in progress" in progress
    assert "passed locally" not in progress


def test_progress_with_no_history_works_and_creates_nothing(
    learner: Learner,
) -> None:
    result = learner.practice("progress")

    assert result.returncode == 0
    assert "No attempts yet" in result.stdout
    assert not learner.practice_dir.exists()


def test_progress_for_a_named_problem_can_report_not_started(
    learner: Learner,
) -> None:
    result = learner.practice("progress", "leetcode", "1")

    assert result.returncode == 0
    assert "not started" in result.stdout


def test_unknown_problem_is_a_clear_usage_error(learner: Learner) -> None:
    result = learner.practice(
        "attempt", "start", "leetcode", "999999", "--package", str(learner.package)
    )

    assert result.returncode == 2
    assert result.stdout == ""
    assert "not in the leetcode catalog" in result.stderr
    assert "Traceback" not in result.stderr
    assert not learner.practice_dir.exists()


def test_missing_package_is_reported_with_exit_3(tmp_path: Path) -> None:
    learner = Learner(tmp_path / "learner", tmp_path / "no-such-package")

    result = learner.practice(
        "attempt", "start", "leetcode", "1", "--package", str(learner.package)
    )

    assert result.returncode == 3
    assert "not a directory" in result.stderr


def test_unknown_attempt_is_a_clear_error(learner: Learner) -> None:
    result = learner.practice("notes", "20261028T000000Z-deadbeef")

    assert result.returncode == 2
    assert "no attempt" in result.stderr


def test_torn_journal_tail_is_reported_and_later_work_continues(
    learner: Learner,
) -> None:
    first = learner.start()
    journal = learner.practice_dir / "journal.jsonl"
    with journal.open("ab") as handle:
        handle.write(b'{"schema_version":1,"event_id":"half-written')

    degraded = learner.practice("attempt", "resume")
    second = learner.start()
    after = learner.practice("attempt", "list")

    assert degraded.returncode == 0
    assert first in degraded.stdout
    assert "journal.jsonl line 2" in degraded.stderr
    assert "interrupted" in degraded.stderr
    assert first in after.stdout
    assert second in after.stdout
    assert "line 2" in after.stderr  # Reported every time; history is never rewritten.


def test_practice_dir_can_come_from_the_environment(
    tmp_path: Path, leetcode_two_sum_package: Path
) -> None:
    learner = Learner(tmp_path / "unused", leetcode_two_sum_package)
    elsewhere = tmp_path / "from-env"
    scripts = Path(sys.executable).parent
    command = next(
        path
        for name in ("practice.exe", "practice")
        if (path := scripts / name).exists()
    )
    environment = {**os.environ, "PRACTICE_DIR": str(elsewhere)}

    result = subprocess.run(
        [
            str(command),
            "attempt",
            "start",
            "leetcode",
            "1",
            "--package",
            str(learner.package),
        ],
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=120,
        check=False,
        env=environment,
    )

    assert result.returncode == 0, result.stdout + result.stderr
    assert (elsewhere / "journal.jsonl").is_file()
    assert not (tmp_path / "unused").exists()


def test_learner_state_is_git_ignored_and_nothing_else_is_written_to_the_repo(
    learner: Learner,
) -> None:
    attempt_id = learner.start()
    ignored = subprocess.run(
        ["git", "check-ignore", "--quiet", ".practice/journal.jsonl"],
        cwd=REPO_ROOT,
        check=False,
    )
    tracked = subprocess.run(
        ["git", "ls-files", ".practice"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=True,
    )

    assert ignored.returncode == 0
    assert tracked.stdout == ""
    assert learner.code_path(attempt_id).is_file()
    assert not (REPO_ROOT / "attempts").exists()
