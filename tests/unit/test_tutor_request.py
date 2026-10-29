# ABOUTME: Unit tests for tutor request selection, reveal scope and spoiler exclusion.
# ABOUTME: They build requests from the real LeetCode 1 package and check the text.

from pathlib import Path

import pytest

from practice.classification import ALL_CLASSES
from practice.history import Attempt, attempt_code_path
from practice.package import ExercisePackage, load_package
from practice.paths import REPO_ROOT
from practice.tutor_policy import find_technique_terms
from practice.tutor_request import (
    ACTIONS,
    RequestError,
    build_request,
    parse_reveal,
)

PACKAGE_DIR = REPO_ROOT / "problems" / "leetcode-1"
MIN_LINE = 30


@pytest.fixture(scope="module")
def package() -> ExercisePackage:
    return load_package(PACKAGE_DIR)


def make_attempt(
    events: list[dict[str, object]] | None = None,
    finished: bool = False,
    timed: bool = False,
    limit_minutes: int | None = None,
) -> Attempt:
    started: dict[str, object] = {
        "type": "attempt_started",
        "attempt_id": "A1",
        "mode": "practice",
        "timed": timed,
    }
    return Attempt(
        attempt_id="A1",
        platform="leetcode",
        problem_id="1",
        title="Two Sum",
        language="python",
        mode="practice",
        timed=timed,
        limit_minutes=limit_minutes,
        started_at="2026-10-28T00:00:00Z",
        events=[started, *(events or [])],
        finished_at="2026-10-28T01:00:00Z" if finished else None,
    )


@pytest.fixture
def practice_dir(tmp_path: Path) -> Path:
    code = attempt_code_path(tmp_path, "leetcode", "1", "A1")
    code.parent.mkdir(parents=True)
    code.write_text("def twoSum(nums, target):\n    return [0, 1]\n", encoding="utf-8")
    return tmp_path


def request(
    practice_dir: Path,
    package: ExercisePackage,
    action: str,
    *,
    mode: str = "practice",
    reveal: str | None = None,
    attempt: Attempt | None = None,
) -> str:
    return build_request(
        practice_dir,
        attempt or make_attempt(),
        package,
        action=action,
        mode=mode,
        reveal=parse_reveal(reveal),
    )


def significant_lines(path: Path) -> set[str]:
    lines = {line.strip() for line in path.read_text(encoding="utf-8").splitlines()}
    return {line for line in lines if len(line) >= MIN_LINE}


def test_every_requested_action_exists() -> None:
    assert set(ACTIONS) >= {
        "hint",
        "explain-solution",
        "review-my-code",
        "explain-my-approach",
        "stuck",
        "concept-refresher",
    }


def test_header_names_platform_problem_attempt_mode_and_action(
    practice_dir: Path, package: ExercisePackage
) -> None:
    text = request(practice_dir, package, "review-my-code")
    assert "Platform: leetcode" in text
    assert "Problem: 1  Two Sum" in text
    assert "Attempt: A1" in text
    assert "Mode: practice" in text
    assert "Action: review-my-code" in text
    assert "tutor/TUTOR.md" in text


def test_mode_is_practice_unless_study_is_chosen(
    practice_dir: Path, package: ExercisePackage
) -> None:
    assert "Mode: study" in request(practice_dir, package, "hint", mode="study")
    with pytest.raises(RequestError, match="mode"):
        request(practice_dir, package, "hint", mode="exam")


def test_timing_is_named_only_when_the_attempt_was_started_timed(
    practice_dir: Path, package: ExercisePackage
) -> None:
    untimed = request(practice_dir, package, "hint")
    assert "Timing: untimed" in untimed
    assert "Timing: timed" not in untimed
    timed = request(practice_dir, package, "hint", attempt=make_attempt(timed=True))
    assert "Timing: timed" in timed
    assert "evidence only" in timed
    assert "minute limit" not in timed


def test_a_timed_request_names_the_limit_chosen_at_start(
    practice_dir: Path, package: ExercisePackage
) -> None:
    attempt = make_attempt(timed=True, limit_minutes=30)

    assert "30 minute limit" in request(practice_dir, package, "hint", attempt=attempt)


def test_statement_is_included_as_open_content(
    practice_dir: Path, package: ExercisePackage
) -> None:
    statement = (PACKAGE_DIR / "statement.md").read_text(encoding="utf-8")
    text = request(practice_dir, package, "concept-refresher")
    assert statement.strip() in text


def test_default_hint_is_the_first_ladder_step(
    practice_dir: Path, package: ExercisePackage
) -> None:
    text = request(practice_dir, package, "hint")
    assert "hint level 0 only" in text
    assert "do not name the technique" in text
    assert "hints/0.md" in text


def test_default_hint_is_the_step_after_the_highest_recorded(
    practice_dir: Path, package: ExercisePackage
) -> None:
    delivered = make_attempt(
        [
            {"type": "assistance", "kind": "hint", "level": 0},
            {"type": "assistance", "kind": "hint", "level": 1},
        ]
    )
    text = request(practice_dir, package, "hint", attempt=delivered)
    assert "hint level 2 only" in text
    assert "hints/2.md" in text
    assert "hints/1.md" not in text


def test_hint_text_beyond_the_permitted_level_never_appears(
    practice_dir: Path, package: ExercisePackage
) -> None:
    statement = significant_lines(PACKAGE_DIR / "statement.md")
    for level in range(4):
        text = request(practice_dir, package, "hint", reveal=str(level))
        assert f"hint level {level} only" in text
        for other in range(4):
            if other == level:
                continue
            assert f"hints/{other}.md" not in text
            leaked = significant_lines(PACKAGE_DIR / "hints" / f"{other}.md")
            for line in leaked - statement:
                assert line not in text


def test_the_permitted_hint_file_is_named_but_its_text_is_not_pasted(
    practice_dir: Path, package: ExercisePackage
) -> None:
    text = request(practice_dir, package, "hint", reveal="1")
    assert "hints/1.md" in text
    statement = significant_lines(PACKAGE_DIR / "statement.md")
    for line in significant_lines(PACKAGE_DIR / "hints" / "1.md") - statement:
        assert line not in text


def test_a_hint_level_that_names_the_technique_says_so(
    practice_dir: Path, package: ExercisePackage
) -> None:
    text = request(practice_dir, package, "hint", reveal="3")
    assert "may name the technique" in text
    assert "do not name the technique" not in text


def test_once_every_level_is_delivered_a_plain_hint_request_fails(
    practice_dir: Path, package: ExercisePackage
) -> None:
    delivered = make_attempt([{"type": "assistance", "kind": "hint", "level": 3}])
    with pytest.raises(RequestError, match="every hint level"):
        request(practice_dir, package, "hint", attempt=delivered)


def test_a_level_the_package_does_not_classify_is_refused(
    practice_dir: Path, package: ExercisePackage
) -> None:
    with pytest.raises(RequestError, match="level 7"):
        request(practice_dir, package, "hint", reveal="7")


def test_notes_and_reference_text_never_appear_in_any_non_reveal_request(
    practice_dir: Path, package: ExercisePackage
) -> None:
    statement = significant_lines(PACKAGE_DIR / "statement.md")
    notes = significant_lines(PACKAGE_DIR / "notes.md") - statement
    assert notes
    for action in ACTIONS:
        if action == "explain-solution":
            continue
        text = request(practice_dir, package, action)
        assert "notes.md" not in text
        for line in notes:
            assert line not in text


def test_no_request_without_the_solution_reveal_names_a_technique(
    practice_dir: Path, package: ExercisePackage
) -> None:
    for action in ACTIONS:
        if action == "explain-solution":
            continue
        for reveal in (None, "0", "1", "2", "3") if action == "hint" else (None,):
            text = request(practice_dir, package, action, reveal=reveal)
            assert find_technique_terms(text) == [], (action, reveal)


def test_explaining_the_solution_requires_the_explicit_reveal(
    practice_dir: Path, package: ExercisePackage
) -> None:
    with pytest.raises(RequestError, match="--reveal solution"):
        request(practice_dir, package, "explain-solution")
    with pytest.raises(RequestError, match="--reveal solution"):
        request(practice_dir, package, "explain-solution", reveal="2")


def test_explicit_solution_reveal_permits_only_the_solution_notes(
    practice_dir: Path, package: ExercisePackage
) -> None:
    text = request(practice_dir, package, "explain-solution", reveal="solution")
    assert "full solution" in text
    assert "notes.md" in text
    assert "this attempt only" in text
    for level in range(4):
        assert f"hints/{level}.md" not in text
    assert "--kind reveal" in text


def test_reveal_is_refused_for_actions_that_have_no_reveal(
    practice_dir: Path, package: ExercisePackage
) -> None:
    for action in ("review-my-code", "explain-my-approach", "stuck"):
        with pytest.raises(RequestError, match="--reveal"):
            request(practice_dir, package, action, reveal="1")
    with pytest.raises(RequestError, match="--reveal"):
        request(practice_dir, package, "hint", reveal="solution")


def test_unsupported_action_is_refused(
    practice_dir: Path, package: ExercisePackage
) -> None:
    with pytest.raises(RequestError, match="unsupported action"):
        request(practice_dir, package, "give-me-the-answer")


def test_code_path_is_given_only_to_actions_that_need_the_code(
    practice_dir: Path, package: ExercisePackage
) -> None:
    code = attempt_code_path(practice_dir, "leetcode", "1", "A1")
    needing = {"hint", "review-my-code", "explain-my-approach", "stuck"}
    for action in ACTIONS:
        text = request(
            practice_dir,
            package,
            action,
            reveal="solution" if action == "explain-solution" else None,
        )
        assert (str(code) in text) == (action in needing), action
    # The code itself is never pasted, only its path.
    assert "return [0, 1]" not in request(practice_dir, package, "review-my-code")


def test_other_attempts_and_private_state_are_withheld(
    practice_dir: Path, package: ExercisePackage
) -> None:
    text = request(practice_dir, package, "review-my-code")
    assert "other attempts" in text
    for name, entry in ALL_CLASSES.items():
        if entry.spoiler:
            assert name in text, name
    assert "teaching_explanation" not in text.split("Withheld")[1]


def test_the_request_asks_the_agent_to_record_help_it_delivers(
    practice_dir: Path, package: ExercisePackage
) -> None:
    text = request(practice_dir, package, "hint")
    assert "practice attempt note-assistance A1 --kind hint --level 0" in text
    assert "nothing has been recorded" in text.replace("\n", " ")


def test_explanation_conversation_points_at_the_assessment_command(
    practice_dir: Path, package: ExercisePackage
) -> None:
    text = request(practice_dir, package, "explain-my-approach")
    assert "practice attempt explain A1" in text
    assert "TUTOR-010" in text


def test_practice_refresher_asks_before_teaching_and_study_may_teach(
    practice_dir: Path, package: ExercisePackage
) -> None:
    practice = request(practice_dir, package, "concept-refresher")
    assert "ask the learner first" in practice
    study = request(practice_dir, package, "concept-refresher", mode="study")
    assert "teach the concept openly" in study
    assert "full solution" in study  # Still not authorized.


def test_finished_attempt_is_unavailable(
    practice_dir: Path, package: ExercisePackage
) -> None:
    with pytest.raises(RequestError, match="finished"):
        request(practice_dir, package, "hint", attempt=make_attempt(finished=True))


def test_package_must_match_the_attempt(
    practice_dir: Path, package: ExercisePackage
) -> None:
    other = make_attempt()
    other.problem_id = "2"
    with pytest.raises(RequestError, match="describes"):
        request(practice_dir, package, "hint", attempt=other)


def test_pending_package_without_a_suite_is_unavailable(
    practice_dir: Path, tmp_path: Path, package: ExercisePackage
) -> None:
    from dataclasses import replace

    pending = replace(package, suite=None)
    with pytest.raises(RequestError, match="not ready"):
        request(practice_dir, pending, "hint")


def test_parse_reveal_accepts_levels_and_solution_only() -> None:
    assert parse_reveal(None) is None
    assert parse_reveal("2") == 2
    assert parse_reveal("solution") == "solution"
    with pytest.raises(RequestError, match="--reveal"):
        parse_reveal("everything")
    with pytest.raises(RequestError, match="--reveal"):
        parse_reveal("-1")
