# ABOUTME: Unit tests for the review ladder, eligibility, skip and reschedule rules.
# ABOUTME: Real journal and attempt files; the clock is PRACTICE_NOW in the environment.

import hashlib
from datetime import date
from pathlib import Path

import pytest

from practice.history import attempt_code_path, journal_for
from practice.reviews import (
    EXPLANATION_CORE_THRESHOLD,
    GAP_DAYS,
    ReviewError,
    ReviewItem,
    ReviewSchedule,
    load_schedule,
    record_reschedule,
    record_skip,
)
from practice.rubric import CORE_MAX

DAY0 = date(2026, 11, 1)
Help = tuple[tuple[str, int | None], ...]


def stamp(day: int, hour: int = 9) -> str:
    return f"{date.fromordinal(DAY0.toordinal() + day).isoformat()}T{hour:02d}:00:00Z"


class Learner:
    """Writes real journal events and attempt files at chosen days."""

    def __init__(self, practice_dir: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        self.practice_dir = practice_dir
        self.monkeypatch = monkeypatch
        self.counter = 0

    def at(self, day: int, hour: int = 9) -> None:
        self.monkeypatch.setenv("PRACTICE_NOW", stamp(day, hour))

    def attempt(
        self,
        day: int,
        *,
        review: bool = False,
        passes: bool = True,
        help: Help = (),
        help_after_pass: Help = (),
        explanation: tuple[int, int, int] | None = None,
        edit_after_pass: bool = False,
        platform: str = "leetcode",
        problem_id: str = "1",
        language: str = "python",
        finish: bool = False,
    ) -> str:
        self.counter += 1
        attempt_id = f"a{self.counter:03d}"
        self.at(day)
        journal = journal_for(self.practice_dir)
        path = attempt_code_path(self.practice_dir, platform, problem_id, attempt_id)
        path.parent.mkdir(parents=True)
        path.write_text("def f():\n    return 1\n", encoding="utf-8")
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        started: dict[str, object] = {
            "attempt_id": attempt_id,
            "platform": platform,
            "problem_id": problem_id,
            "title": "Some Problem",
            "language": language,
            "mode": "practice",
            "timed": False,
        }
        if review:
            started["review"] = True
        journal.append("attempt_started", **started)
        for kind, level in help:
            journal.append("assistance", attempt_id=attempt_id, kind=kind, level=level)
        journal.append(
            "test_run",
            attempt_id=attempt_id,
            status="passed" if passes else "failed",
            message="m",
            code_sha256=digest,
        )
        for kind, level in help_after_pass:
            journal.append("assistance", attempt_id=attempt_id, kind=kind, level=level)
        if explanation is not None:
            approach, correctness, time = explanation
            journal.append(
                "explanation_assessment",
                attempt_id=attempt_id,
                approach=approach,
                correctness=correctness,
                time_complexity=time,
                space_complexity=None,
                evidence="e",
                feedback="f",
                code_sha256=digest,
            )
        if edit_after_pass:
            path.write_text("def f():\n    return 2\n", encoding="utf-8")
        if finish:
            journal.append("attempt_finished", attempt_id=attempt_id)
        return attempt_id

    def schedule(self, day: int) -> ReviewSchedule:
        self.at(day)
        return load_schedule(self.practice_dir)

    def item(self, day: int, problem_id: str = "1") -> ReviewItem:
        found = [i for i in self.schedule(day).items if i.problem_id == problem_id]
        assert len(found) == 1
        return found[0]


@pytest.fixture
def learner(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Learner:
    return Learner(tmp_path / "learner", monkeypatch)


def due_day(item: ReviewItem) -> int:
    return item.due_on.toordinal() - DAY0.toordinal()


def test_the_ladder_is_one_three_seven_fourteen_thirty_days() -> None:
    assert GAP_DAYS == (1, 3, 7, 14, 30)


def test_an_empty_journal_has_nothing_scheduled(learner: Learner) -> None:
    schedule = learner.schedule(0)

    assert schedule.items == []
    assert schedule.notices == []


def test_the_first_pass_schedules_a_one_day_review_anchored_to_the_pass(
    learner: Learner,
) -> None:
    learner.attempt(day=2)

    item = learner.item(day=2)

    assert item.gap_days == 1
    assert item.rung == 0
    assert item.practiced_on == date(2026, 11, 3)
    assert item.due_on == date(2026, 11, 4)
    assert not item.is_due(date(2026, 11, 3))
    assert item.is_due(date(2026, 11, 4))


def test_a_first_pass_with_help_still_gets_the_one_day_review(
    learner: Learner,
) -> None:
    learner.attempt(day=0, help=(("reveal", None),))

    assert learner.item(day=0).gap_days == 1


@pytest.mark.parametrize("review", [False, True])
def test_an_attempt_that_never_passed_is_not_review_eligible(
    learner: Learner, review: bool
) -> None:
    learner.attempt(day=0, passes=False, review=review)

    assert learner.schedule(5).items == []


def test_independent_reviews_climb_the_whole_ladder_and_stay_at_thirty(
    learner: Learner,
) -> None:
    learner.attempt(day=0)
    day = 0
    seen = []
    for _ in range(6):
        day = due_day(learner.item(day))
        learner.attempt(day=day, review=True)
        seen.append(learner.item(day).gap_days)

    assert seen == [3, 7, 14, 30, 30, 30]


def test_the_gap_is_counted_from_the_actual_review_date_not_the_due_date(
    learner: Learner,
) -> None:
    learner.attempt(day=0)
    assert due_day(learner.item(0)) == 1

    learner.attempt(day=10, review=True)

    assert due_day(learner.item(10)) == 13  # Day 10 plus the 3 day gap.


def climb_to_seven_day_rung(learner: Learner) -> int:
    learner.attempt(day=0)
    learner.attempt(day=1, review=True)  # Now a 3 day gap.
    learner.attempt(day=4, review=True)  # Now a 7 day gap.
    assert learner.item(4).gap_days == 7
    return 4


@pytest.mark.parametrize(
    ("help", "expected_gap"),
    [
        ((("hint", 0),), 3),
        ((("hint", 3),), 3),
        ((("concept", None),), 7),
        ((("reveal", None),), 1),
        ((("concept", None), ("hint", 1), ("reveal", None)), 1),
    ],
)
def test_help_during_a_review_holds_or_shortens_the_gap(
    learner: Learner, help: Help, expected_gap: int
) -> None:
    day = climb_to_seven_day_rung(learner)

    learner.attempt(day=day + 7, review=True, help=help)

    assert learner.item(day + 7).gap_days == expected_gap


def test_help_never_lengthens_the_gap(learner: Learner) -> None:
    learner.attempt(day=0)

    learner.attempt(day=1, review=True, help=(("concept", None),))

    assert learner.item(1).gap_days == 1


def test_help_after_the_pass_does_not_count_against_the_review(
    learner: Learner,
) -> None:
    learner.attempt(day=0)

    learner.attempt(day=1, review=True, help_after_pass=(("reveal", None),))

    assert learner.item(1).gap_days == 3


def test_a_pass_gone_stale_by_a_later_edit_does_not_advance(
    learner: Learner,
) -> None:
    learner.attempt(day=0)

    learner.attempt(day=1, review=True, edit_after_pass=True)

    assert learner.item(1).gap_days == 1


def test_a_weak_explanation_resets_to_the_shortest_gap(learner: Learner) -> None:
    day = climb_to_seven_day_rung(learner)
    weak = (3, 3, 0)
    assert sum(weak) < EXPLANATION_CORE_THRESHOLD

    learner.attempt(day=day + 7, review=True, explanation=weak)

    assert learner.item(day + 7).gap_days == 1


def test_an_explanation_at_the_threshold_still_advances(learner: Learner) -> None:
    learner.attempt(day=0)
    at_threshold = (4, 3, 0)
    assert sum(at_threshold) == EXPLANATION_CORE_THRESHOLD

    learner.attempt(day=1, review=True, explanation=at_threshold)

    assert learner.item(1).gap_days == 3


def test_the_threshold_is_below_the_perfect_score() -> None:
    assert 0 < EXPLANATION_CORE_THRESHOLD < CORE_MAX


def test_a_plain_later_attempt_does_not_move_the_ladder(learner: Learner) -> None:
    learner.attempt(day=0)

    learner.attempt(day=0)  # Another ordinary attempt, not marked as a review.

    item = learner.item(0)
    assert item.gap_days == 1
    assert item.due_on == date(2026, 11, 2)


def test_python_and_other_languages_are_scheduled_separately(
    learner: Learner,
) -> None:
    learner.attempt(day=0, language="python")
    learner.attempt(day=0, language="rust")
    learner.attempt(day=1, review=True, language="python")

    schedule = learner.schedule(1)

    by_language = {i.language: i for i in schedule.items}
    assert by_language["python"].gap_days == 3
    assert by_language["rust"].gap_days == 1


def test_platforms_and_problems_are_scheduled_separately(learner: Learner) -> None:
    learner.attempt(day=0, problem_id="1")
    learner.attempt(day=0, problem_id="217")
    learner.attempt(day=0, problem_id="1", platform="codeforces")
    learner.attempt(day=1, review=True, problem_id="217")

    schedule = learner.schedule(1)

    identities = {(i.platform, i.problem_id): i.gap_days for i in schedule.items}
    assert identities == {
        ("leetcode", "1"): 1,
        ("leetcode", "217"): 3,
        ("codeforces", "1"): 1,
    }


def test_skipping_moves_the_date_by_the_current_gap_and_keeps_the_rung(
    learner: Learner,
) -> None:
    learner.attempt(day=0)
    learner.attempt(day=1, review=True)  # A 3 day gap, due on day 4.
    item = learner.item(1)

    learner.at(9)  # Long overdue when the learner skips it.
    record_skip(learner.practice_dir, item)

    after = learner.item(9)
    assert after.gap_days == 3
    assert after.rung == item.rung
    assert due_day(after) == 12
    assert after.practiced_on == item.practiced_on


def test_rescheduling_sets_the_exact_date(learner: Learner) -> None:
    learner.attempt(day=0)
    item = learner.item(0)

    learner.at(0)
    record_reschedule(learner.practice_dir, item, date(2026, 11, 20))

    after = learner.item(0)
    assert after.due_on == date(2026, 11, 20)
    assert after.gap_days == 1


def test_a_later_review_replaces_an_earlier_reschedule(learner: Learner) -> None:
    learner.attempt(day=0)
    learner.at(0)
    record_reschedule(learner.practice_dir, learner.item(0), date(2026, 11, 20))

    learner.attempt(day=2, review=True)

    assert due_day(learner.item(2)) == 5


def test_the_latest_of_several_skips_and_reschedules_wins(learner: Learner) -> None:
    learner.attempt(day=0)
    learner.at(2)
    record_skip(learner.practice_dir, learner.item(2))
    learner.at(3)
    record_reschedule(learner.practice_dir, learner.item(3), date(2026, 12, 1))
    learner.at(4)
    record_skip(learner.practice_dir, learner.item(4))

    assert due_day(learner.item(4)) == 5  # Day 4 plus the 1 day gap.


def test_skip_and_reschedule_need_a_scheduled_review(learner: Learner) -> None:
    learner.attempt(day=0)
    stranger = ReviewItem(
        platform="leetcode",
        problem_id="999",
        title="Missing",
        language="python",
        rung=0,
        gap_days=1,
        practiced_on=DAY0,
        due_on=DAY0,
        open_attempt_id=None,
        adjusted=None,
    )

    with pytest.raises(ReviewError, match="999"):
        record_skip(learner.practice_dir, stranger)
    with pytest.raises(ReviewError, match="999"):
        record_reschedule(learner.practice_dir, stranger, DAY0)


def test_skip_and_reschedule_are_events_in_the_journal_and_nothing_else(
    learner: Learner,
) -> None:
    learner.attempt(day=0)
    before = journal_for(learner.practice_dir).read().records
    learner.at(5)

    record_skip(learner.practice_dir, learner.item(5))
    record_reschedule(learner.practice_dir, learner.item(5), date(2026, 12, 25))

    after = journal_for(learner.practice_dir).read().records
    assert after[: len(before)] == before
    new = after[len(before) :]
    assert [r["type"] for r in new] == ["review_skipped", "review_rescheduled"]
    assert new[0]["language"] == "python"
    assert new[1]["due_on"] == "2026-12-25"
    names = {p.name for p in learner.practice_dir.iterdir()}
    assert names == {"attempts", "journal.jsonl", "journal.jsonl.lock"}


def test_due_and_upcoming_are_split_by_the_date_and_ordered(learner: Learner) -> None:
    learner.attempt(day=0, problem_id="217")
    learner.attempt(day=0, problem_id="1")
    learner.attempt(day=5, problem_id="3")
    schedule = learner.schedule(1)

    due = schedule.due(date(2026, 11, 2))
    upcoming = schedule.upcoming(date(2026, 11, 2))

    assert [i.problem_id for i in due] == ["1", "217"]
    assert [i.problem_id for i in upcoming] == ["3"]


def test_an_unfinished_review_attempt_is_reported_until_it_passes(
    learner: Learner,
) -> None:
    learner.attempt(day=0)
    started = learner.attempt(day=1, review=True, passes=False)

    assert learner.item(1).open_attempt_id == started

    learner.attempt(day=1, review=True)
    assert learner.item(1).open_attempt_id is None


def test_a_finished_review_attempt_is_not_reported_as_open(learner: Learner) -> None:
    learner.attempt(day=0)
    learner.attempt(day=1, review=True, passes=False, finish=True)

    assert learner.item(1).open_attempt_id is None
    assert learner.item(1).gap_days == 1  # Unchanged: no pass, no outcome.


def test_review_events_with_bad_data_are_reported_and_ignored(
    learner: Learner,
) -> None:
    learner.attempt(day=0)
    learner.at(1)
    journal = journal_for(learner.practice_dir)
    journal.append("review_rescheduled", platform="leetcode", problem_id="1")
    journal.append(
        "review_rescheduled",
        platform="leetcode",
        problem_id="1",
        language="python",
        due_on="soon",
    )
    journal.append("review_skipped", platform="leetcode")

    schedule = learner.schedule(1)

    assert len(schedule.notices) == 3
    assert schedule.items[0].due_on == date(2026, 11, 2)


def test_loading_a_schedule_writes_nothing(learner: Learner) -> None:
    learner.attempt(day=0)
    before = (learner.practice_dir / "journal.jsonl").read_bytes()

    learner.schedule(5)

    assert (learner.practice_dir / "journal.jsonl").read_bytes() == before
