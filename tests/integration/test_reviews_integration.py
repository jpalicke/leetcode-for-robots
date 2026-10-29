# ABOUTME: Integration tests for review commands over real journal and attempt files.
# ABOUTME: Real Two Sum package and runner; time comes from PRACTICE_NOW.

import re
import shutil
from pathlib import Path

import pytest

from practice.cli import main
from practice.history import attempt_code_path, load_history
from practice.journal import Journal
from practice.menu import CommandResult, capture_command
from practice.paths import REPO_ROOT

HASH_MAP = (
    REPO_ROOT / "tests" / "fixtures" / "leetcode_two_sum_solutions" / "hash_map.py"
)
SECRET = "seen = {}"  # A line of the solution that must never be printed in a review.
STARTER = REPO_ROOT / "problems" / "leetcode-1" / "starter.py"


class Session:
    """Runs the real CLI in this process against one learner folder."""

    def __init__(
        self, practice_dir: Path, package: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        self.practice_dir = practice_dir
        self.package = package
        self.monkeypatch = monkeypatch

    def day(self, iso_day: str) -> None:
        self.monkeypatch.setenv("PRACTICE_NOW", f"{iso_day}T09:00:00Z")

    def run(self, *argv: str) -> CommandResult:
        return capture_command(main, ["--practice-dir", str(self.practice_dir), *argv])

    def ok(self, *argv: str) -> CommandResult:
        result = self.run(*argv)
        assert result.code == 0, result.stdout + result.stderr
        return result

    def start(self, *extra: str, review: bool = False) -> str:
        command = ["review"] if review else ["attempt"]
        result = self.ok(
            *command, "start", "leetcode", "1", "--package", str(self.package), *extra
        )
        match = re.search(r"Started (?:review )?attempt (\S+)", result.stdout)
        assert match is not None, result.stdout
        return match.group(1)

    def solve(self, attempt_id: str) -> None:
        code = attempt_code_path(self.practice_dir, "leetcode", "1", attempt_id)
        shutil.copyfile(HASH_MAP, code)
        self.ok("attempt", "test", attempt_id, "--package", str(self.package))

    def records(self) -> list[dict[str, object]]:
        return Journal(self.practice_dir / "journal.jsonl").read().records


@pytest.fixture
def session(
    tmp_path: Path, problems_dir: Path, monkeypatch: pytest.MonkeyPatch
) -> Session:
    return Session(tmp_path / "learner", problems_dir / "leetcode-1", monkeypatch)


def first_pass(session: Session, iso_day: str = "2026-11-01") -> str:
    session.day(iso_day)
    attempt_id = session.start()
    session.solve(attempt_id)
    return attempt_id


def test_review_list_with_no_history_says_nothing_is_scheduled(
    session: Session,
) -> None:
    session.day("2026-11-01")

    result = session.ok("review", "list")

    assert "No reviews scheduled" in result.stdout
    assert not session.practice_dir.exists()


def test_passing_two_sum_schedules_a_review_for_the_next_day(session: Session) -> None:
    first_pass(session)

    same_day = session.ok("review", "list").stdout
    session.day("2026-11-02")
    next_day = session.ok("review", "list").stdout

    assert "Due now:\n  (none)" in same_day
    assert "Upcoming:" in same_day
    assert "leetcode 1  Two Sum  (python)  due 2026-11-02  rung 1 of 5" in same_day
    assert "Due now:\n  leetcode 1  Two Sum" in next_day
    assert "due 2026-11-02" in next_day
    assert "Upcoming:\n  (none)" in next_day


def test_starting_a_review_makes_a_blank_marked_attempt_and_hides_the_old_code(
    session: Session,
) -> None:
    earlier = first_pass(session)
    earlier_code = attempt_code_path(session.practice_dir, "leetcode", "1", earlier)
    earlier_bytes = earlier_code.read_bytes()
    assert SECRET in earlier_bytes.decode()
    session.day("2026-11-02")

    result = session.ok(
        "review", "start", "leetcode", "1", "--package", str(session.package)
    )

    review_id = re.search(r"Started review attempt (\S+)", result.stdout)
    assert review_id is not None
    new_code = attempt_code_path(
        session.practice_dir, "leetcode", "1", review_id.group(1)
    )
    assert new_code.read_bytes() == STARTER.read_bytes()
    assert earlier_code.read_bytes() == earlier_bytes
    assert SECRET not in result.stdout + result.stderr
    assert earlier not in result.stdout + result.stderr
    assert "Earlier solutions are kept on disk and are not shown" in result.stdout
    started = [r for r in session.records() if r["type"] == "attempt_started"][-1]
    assert started["review"] is True
    assert started["starter_source"] == "package starter"
    attempt = load_history(session.practice_dir).attempts[-1]
    assert attempt.review


def test_a_review_attempt_never_prints_earlier_code_anywhere(session: Session) -> None:
    first_pass(session)
    session.day("2026-11-02")
    review_id = session.start(review=True)

    outputs = [
        session.ok("review", "list"),
        session.ok("attempt", "resume"),
        session.ok("attempt", "list"),
        session.ok("progress"),
        session.ok("notes", review_id),
        session.ok("menu"),
        session.ok("menu", "--reviews"),
    ]

    for result in outputs:
        assert SECRET not in result.stdout + result.stderr


def test_a_review_attempt_resumes_tests_and_shows_its_marker(session: Session) -> None:
    first_pass(session)
    session.day("2026-11-02")
    review_id = session.start(review=True)

    resumed = session.ok("attempt", "resume")
    listed = session.ok("review", "list")
    session.solve(review_id)
    notes = session.ok("notes", review_id)

    assert review_id in resumed.stdout
    assert "review" in resumed.stdout
    assert f"review in progress: attempt {review_id}" in listed.stdout
    assert "review" in notes.stdout.splitlines()[1]


def test_a_passed_independent_review_advances_to_three_days_from_that_day(
    session: Session,
) -> None:
    first_pass(session)
    session.day("2026-11-05")  # Three days late, which costs nothing.
    review_id = session.start(review=True)
    session.solve(review_id)

    listing = session.ok("review", "list").stdout

    assert "due 2026-11-08  rung 2 of 5 (3 day gap)" in listing


def test_help_in_a_review_pulls_the_next_date_back_to_one_day(
    session: Session,
) -> None:
    first_pass(session)
    session.day("2026-11-02")
    review_id = session.start(review=True)
    session.ok("attempt", "note-assistance", review_id, "--kind", "reveal")
    session.solve(review_id)

    listing = session.ok("review", "list").stdout

    assert "due 2026-11-03  rung 1 of 5 (1 day gap)" in listing


def test_starting_a_review_before_it_is_due_is_allowed_and_says_so(
    session: Session,
) -> None:
    first_pass(session)

    result = session.ok(
        "review", "start", "leetcode", "1", "--package", str(session.package)
    )

    assert "not due until 2026-11-02" in result.stdout


def test_a_problem_that_was_never_passed_cannot_be_reviewed(session: Session) -> None:
    session.day("2026-11-01")
    session.start()
    before = session.records()

    result = session.run(
        "review", "start", "leetcode", "1", "--package", str(session.package)
    )

    assert result.code == 2
    assert "no review is scheduled" in result.stderr
    assert session.records() == before


def test_a_second_review_cannot_start_while_one_is_open(session: Session) -> None:
    first_pass(session)
    session.day("2026-11-02")
    open_id = session.start(review=True)
    before = session.records()

    result = session.run(
        "review", "start", "leetcode", "1", "--package", str(session.package)
    )

    assert result.code == 2
    assert open_id in result.stderr
    assert "attempt resume" in result.stderr
    assert session.records() == before


def test_skip_records_an_event_and_moves_the_date_without_penalty(
    session: Session,
) -> None:
    first_pass(session)
    session.day("2026-11-10")

    result = session.ok("review", "skip", "leetcode", "1")

    assert "No score is affected" in result.stdout
    assert "2026-11-11" in result.stdout
    assert session.records()[-1]["type"] == "review_skipped"
    listing = session.ok("review", "list").stdout
    assert "due 2026-11-11  rung 1 of 5" in listing
    assert "skipped" in listing


def test_reschedule_on_a_date_and_in_days(session: Session) -> None:
    first_pass(session)
    session.day("2026-11-02")

    session.ok("review", "reschedule", "leetcode", "1", "--on", "2026-12-25")
    assert "due 2026-12-25" in session.ok("review", "list").stdout
    session.ok("review", "reschedule", "leetcode", "1", "--in-days", "4")

    listing = session.ok("review", "list").stdout
    assert "due 2026-11-06" in listing
    assert "rescheduled" in listing
    types = [r["type"] for r in session.records()]
    assert types[-2:] == ["review_rescheduled", "review_rescheduled"]


@pytest.mark.parametrize(
    "extra",
    [
        [],
        ["--on", "2026-12-25", "--in-days", "3"],
        ["--on", "next week"],
        ["--in-days", "-2"],
        ["--on", "2026-10-01"],
    ],
)
def test_reschedule_rejects_bad_dates_and_writes_nothing(
    session: Session, extra: list[str]
) -> None:
    first_pass(session)
    session.day("2026-11-02")
    before = session.records()

    result = session.run("review", "reschedule", "leetcode", "1", *extra)

    assert result.code == 2
    assert session.records() == before


def test_skip_and_reschedule_refuse_an_unscheduled_problem(session: Session) -> None:
    session.day("2026-11-01")

    skipped = session.run("review", "skip", "leetcode", "1")
    moved = session.run("review", "reschedule", "leetcode", "1", "--in-days", "2")

    assert skipped.code == moved.code == 2
    assert not session.practice_dir.exists()


def test_the_review_language_is_part_of_the_identity(session: Session) -> None:
    first_pass(session)
    session.day("2026-11-02")

    result = session.run("review", "skip", "leetcode", "1", "--language", "rust")

    assert result.code != 0  # Only python is a known language; none is scheduled.


def test_a_bad_practice_now_is_a_clear_error(
    session: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("PRACTICE_NOW", "tomorrow-ish")

    result = session.run("review", "list")

    assert result.code == 2
    assert "PRACTICE_NOW" in result.stderr


def test_the_journal_stays_the_only_store(session: Session) -> None:
    first_pass(session)
    session.day("2026-11-02")
    session.ok("review", "skip", "leetcode", "1")
    session.ok("review", "list")

    names = sorted(p.name for p in session.practice_dir.iterdir())
    assert names == ["attempts", "journal.jsonl", "journal.jsonl.lock"]


def test_dates_follow_the_utc_day_of_the_pass(
    session: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("PRACTICE_NOW", "2026-11-01T23:30:00-05:00")  # 04:30 UTC, Nov 2.
    attempt_id = session.start()
    session.solve(attempt_id)

    listing = session.ok("review", "list").stdout

    assert "due 2026-11-03" in listing
