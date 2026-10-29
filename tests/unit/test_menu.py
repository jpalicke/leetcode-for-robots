# ABOUTME: Unit tests for the shared menu core: state, items, availability and refusals.
# ABOUTME: Real files in temp folders and the real CLI; no terminal library needed.

import json
from pathlib import Path

import pytest

from practice.attempts import finish_attempt
from practice.history import AttemptError, find_attempt, load_history
from practice.menu import (
    MAIN,
    Item,
    Menu,
    MenuEnvironment,
    MenuError,
    Screen,
    build_menu,
    choose,
)
from practice.tutor_policy import find_technique_terms


def keys(menu: Menu) -> list[str]:
    return [item.key for item in menu.items]


def item(menu: Menu, key: str) -> Item:
    return next(i for i in menu.items if i.key == key)


def number_of(menu: Menu, key: str) -> int:
    return keys(menu).index(key) + 1


def journal_bytes(env: MenuEnvironment) -> bytes:
    path = env.practice_dir / "journal.jsonl"
    return path.read_bytes() if path.exists() else b""


def start_two_sum(env: MenuEnvironment) -> str:
    browse = Screen("problem", platform="leetcode", problem_id="1")
    menu = build_menu(env, browse)
    result = choose(env, browse, number_of(menu, "start"))
    assert result.code == 0, result.stderr
    assert result.next_screen.kind == "attempt"
    return result.next_screen.attempt_id


def test_main_menu_with_no_history_has_the_documented_items(
    menu_env: MenuEnvironment,
) -> None:
    menu = build_menu(menu_env, MAIN)

    assert keys(menu) == [
        "resume",
        "browse",
        "progress",
        "reviews",
        "recommendations",
        "study",
        "timed",
    ]
    assert not item(menu, "resume").available
    assert item(menu, "resume").reason
    assert item(menu, "browse").available
    assert item(menu, "progress").available


@pytest.mark.parametrize("key", ["study"])
def test_future_features_are_listed_but_say_not_available_yet(
    menu_env: MenuEnvironment, key: str
) -> None:
    entry = item(build_menu(menu_env, MAIN), key)

    assert not entry.available
    assert entry.reason is not None
    assert "not available yet" in entry.reason.lower()


@pytest.mark.parametrize("key", ["study"])
def test_choosing_a_future_feature_does_nothing_and_does_not_claim_success(
    menu_env: MenuEnvironment, key: str
) -> None:
    menu = build_menu(menu_env, MAIN)
    before = journal_bytes(menu_env)

    result = choose(menu_env, MAIN, number_of(menu, key))

    assert result.code != 0
    assert "not available yet" in result.stdout.lower()
    assert "nothing was done" in result.stdout.lower()
    assert result.next_screen == MAIN
    assert journal_bytes(menu_env) == before
    assert not (menu_env.practice_dir / "attempts").exists()


def test_resume_is_refused_when_there_is_no_active_attempt(
    menu_env: MenuEnvironment,
) -> None:
    menu = build_menu(menu_env, MAIN)

    result = choose(menu_env, MAIN, number_of(menu, "resume"))

    assert result.code != 0
    assert "nothing was done" in result.stdout.lower()


def test_main_menu_offers_resume_once_an_attempt_is_active(
    menu_env: MenuEnvironment,
) -> None:
    attempt_id = start_two_sum(menu_env)

    menu = build_menu(menu_env, MAIN)

    assert item(menu, "resume").available
    assert any(attempt_id in line for line in menu.lines)
    result = choose(menu_env, MAIN, number_of(menu, "resume"))
    assert result.code == 0
    assert attempt_id in result.stdout
    assert result.next_screen == Screen("attempt", attempt_id=attempt_id)


def test_choosing_a_number_outside_the_menu_is_an_error(
    menu_env: MenuEnvironment,
) -> None:
    with pytest.raises(MenuError, match="1 to 7"):
        choose(menu_env, MAIN, 8)
    with pytest.raises(MenuError):
        choose(menu_env, MAIN, 0)


def test_browse_by_words_lists_ready_problems_as_selectable(
    menu_env: MenuEnvironment,
) -> None:
    screen = Screen("browse", words=("two", "sum"))

    menu = build_menu(menu_env, screen)

    two_sum = next(i for i in menu.items if i.problem == ("leetcode", "1"))
    assert two_sum.available
    assert "Two Sum" in two_sum.label
    assert keys(menu)[-1] == "main"


def test_browse_shows_a_problem_with_no_package_as_pending(
    menu_env: MenuEnvironment,
) -> None:
    screen = Screen("browse", words=("add", "two", "numbers"))
    menu = build_menu(menu_env, screen)
    pending = next(i for i in menu.items if i.problem == ("leetcode", "2"))
    before = journal_bytes(menu_env)

    result = choose(menu_env, screen, menu.items.index(pending) + 1)

    assert not pending.available
    assert pending.reason is not None
    assert pending.reason.lower().startswith("pending")
    assert result.code != 0
    assert "pending" in result.stdout.lower()
    assert "nothing was done" in result.stdout.lower()
    assert result.next_screen == screen
    assert journal_bytes(menu_env) == before


def test_browse_without_words_lists_every_package_ready_or_pending(
    menu_env: MenuEnvironment, stub_only_id: str
) -> None:
    menu = build_menu(menu_env, Screen("browse"))

    by_problem = {i.problem: i for i in menu.items if i.problem}
    assert by_problem[("leetcode", "1")].available
    stub = by_problem[("leetcode", stub_only_id)]
    assert not stub.available
    assert stub.reason is not None and stub.reason.lower().startswith("pending")


def test_a_stub_only_package_can_never_be_started(
    menu_env: MenuEnvironment, stub_only_id: str
) -> None:
    screen = Screen("problem", platform="leetcode", problem_id=stub_only_id)
    menu = build_menu(menu_env, screen)
    before = journal_bytes(menu_env)

    result = choose(menu_env, screen, number_of(menu, "start"))

    assert not item(menu, "start").available
    assert result.code != 0
    assert "pending" in result.stdout.lower()
    assert journal_bytes(menu_env) == before
    assert not (menu_env.practice_dir / "attempts").exists()


def test_a_package_with_a_blocker_is_pending_and_cannot_be_started(
    menu_env: MenuEnvironment, problems_dir: Path
) -> None:
    record_path = problems_dir / "leetcode-1" / "readiness.json"
    record = json.loads(record_path.read_text(encoding="utf-8"))
    record["blockers"] = ["a blocking problem"]
    record_path.write_text(json.dumps(record), encoding="utf-8")

    menu = build_menu(menu_env, Screen("problem", platform="leetcode", problem_id="1"))

    assert not item(menu, "start").available
    assert "pending" in (item(menu, "start").reason or "").lower()


def test_the_problem_menu_starts_an_untimed_practice_attempt(
    menu_env: MenuEnvironment,
) -> None:
    attempt_id = start_two_sum(menu_env)

    records = [
        json.loads(line)
        for line in journal_bytes(menu_env).decode("utf-8").splitlines()
    ]
    assert [r["type"] for r in records] == ["attempt_started"]
    assert records[0]["attempt_id"] == attempt_id
    assert records[0]["mode"] == "practice"
    assert records[0]["timed"] is False


def test_the_problem_menu_offers_resume_for_its_unfinished_attempt(
    menu_env: MenuEnvironment,
) -> None:
    attempt_id = start_two_sum(menu_env)
    screen = Screen("problem", platform="leetcode", problem_id="1")

    menu = build_menu(menu_env, screen)

    resume = item(menu, "resume-problem")
    assert resume.available
    assert resume.attempt_id == attempt_id


def test_an_unknown_problem_screen_is_an_error(menu_env: MenuEnvironment) -> None:
    with pytest.raises(MenuError, match="catalog"):
        build_menu(menu_env, Screen("problem", platform="leetcode", problem_id="99999"))


def test_the_attempt_menu_offers_the_contextual_actions(
    menu_env: MenuEnvironment,
) -> None:
    attempt_id = start_two_sum(menu_env)

    menu = build_menu(menu_env, Screen("attempt", attempt_id=attempt_id))

    assert keys(menu) == [
        "test",
        "hint",
        "explain-approach",
        "explain-solution",
        "notes",
        "main",
    ]
    assert all(i.available for i in menu.items)
    assert item(menu, "explain-solution").confirm
    assert not any(i.confirm for i in menu.items if i.key != "explain-solution")


def test_a_finished_attempt_cannot_be_tested_or_asked_about(
    menu_env: MenuEnvironment,
) -> None:
    attempt_id = start_two_sum(menu_env)
    screen = Screen("attempt", attempt_id=attempt_id)
    finished = menu_env.run(["attempt", "finish", attempt_id])
    assert finished.code == 0

    menu = build_menu(menu_env, screen)

    for key in ("test", "hint", "explain-approach", "explain-solution"):
        assert not item(menu, key).available
        assert "finished" in (item(menu, key).reason or "")
    assert item(menu, "notes").available


def test_an_attempt_whose_package_is_not_ready_is_not_runnable(
    menu_env: MenuEnvironment, problems_dir: Path
) -> None:
    attempt_id = start_two_sum(menu_env)
    (problems_dir / "leetcode-1" / "tests.json").unlink()

    menu = build_menu(menu_env, Screen("attempt", attempt_id=attempt_id))

    for key in ("test", "hint", "explain-approach", "explain-solution"):
        assert not item(menu, key).available
        assert "pending" in (item(menu, key).reason or "").lower()


def test_an_unknown_attempt_is_an_error(menu_env: MenuEnvironment) -> None:
    with pytest.raises(AttemptError):
        build_menu(menu_env, Screen("attempt", attempt_id="nope"))


def test_the_full_solution_needs_confirmation_and_prepares_nothing_without_it(
    menu_env: MenuEnvironment,
) -> None:
    attempt_id = start_two_sum(menu_env)
    screen = Screen("attempt", attempt_id=attempt_id)
    number = number_of(build_menu(menu_env, screen), "explain-solution")
    before = journal_bytes(menu_env)

    refused = choose(menu_env, screen, number)

    assert refused.code != 0
    assert "confirm" in refused.stdout.lower()
    assert "nothing was done" in refused.stdout.lower()
    assert not (menu_env.practice_dir / "requests").exists()

    granted = choose(menu_env, screen, number, confirmed=True)

    assert granted.code == 0, granted.stderr
    assert "Action: explain-solution" in granted.stdout
    assert journal_bytes(menu_env) == before  # Preparing a request records nothing.


def test_a_hint_request_is_prepared_but_no_hint_is_recorded_as_given(
    menu_env: MenuEnvironment,
) -> None:
    attempt_id = start_two_sum(menu_env)
    screen = Screen("attempt", attempt_id=attempt_id)
    before = journal_bytes(menu_env)

    result = choose(menu_env, screen, number_of(build_menu(menu_env, screen), "hint"))

    assert result.code == 0, result.stderr
    assert "Action: hint" in result.stdout
    assert "hint level 0 only" in result.stdout
    assert journal_bytes(menu_env) == before
    assert "assistance" not in journal_bytes(menu_env).decode("utf-8")


def started_flags(menu_env: MenuEnvironment) -> list[object]:
    return [
        json.loads(line).get("timed")
        for line in journal_bytes(menu_env).decode("utf-8").splitlines()
        if json.loads(line)["type"] == "attempt_started"
    ]


def test_timed_practice_is_an_available_main_menu_item(
    menu_env: MenuEnvironment,
) -> None:
    entry = item(build_menu(menu_env, MAIN), "timed")

    assert entry.available
    assert entry.reason is None


def test_choosing_timed_practice_only_opens_the_timed_list_and_writes_nothing(
    menu_env: MenuEnvironment,
) -> None:
    menu = build_menu(menu_env, MAIN)

    result = choose(menu_env, MAIN, number_of(menu, "timed"))

    assert result.code == 0, result.stderr
    assert result.next_screen == Screen("browse", timed=True)
    assert journal_bytes(menu_env) == b""
    assert not (menu_env.practice_dir / "attempts").exists()


def test_the_timed_list_leads_to_a_problem_menu_that_offers_the_timed_start_first(
    menu_env: MenuEnvironment,
) -> None:
    browse = Screen("browse", timed=True)
    menu = build_menu(menu_env, browse)
    chosen = choose(
        menu_env, browse, [i.problem for i in menu.items].index(("leetcode", "1")) + 1
    )

    assert chosen.next_screen == Screen(
        "problem", platform="leetcode", problem_id="1", timed=True
    )
    problem = build_menu(menu_env, chosen.next_screen)
    assert keys(problem)[:2] == ["start-timed", "start"]
    assert "timed" in item(problem, "start-timed").label.lower()


def test_the_untimed_problem_menu_lists_both_starts_with_untimed_first(
    menu_env: MenuEnvironment,
) -> None:
    menu = build_menu(menu_env, Screen("problem", platform="leetcode", problem_id="1"))

    assert keys(menu)[:2] == ["start", "start-timed"]


def test_the_timed_start_records_a_timed_attempt_and_the_next_start_is_untimed(
    menu_env: MenuEnvironment,
) -> None:
    problem = Screen("problem", platform="leetcode", problem_id="1", timed=True)
    menu = build_menu(menu_env, problem)

    timed = choose(menu_env, problem, number_of(menu, "start-timed"))

    assert timed.code == 0, timed.stderr
    assert started_flags(menu_env) == [True]
    assert not timed.next_screen.timed
    # Finish it so the problem menu offers a fresh start, then start again.
    finish_attempt(
        menu_env.practice_dir,
        find_attempt(load_history(menu_env.practice_dir), timed.next_screen.attempt_id),
    )
    fresh = Screen("problem", platform="leetcode", problem_id="1")
    plain = choose(menu_env, fresh, number_of(build_menu(menu_env, fresh), "start"))
    assert plain.code == 0, plain.stderr
    assert started_flags(menu_env) == [True, False]


def test_testing_from_the_menu_never_turns_timing_on(
    menu_env: MenuEnvironment,
) -> None:
    attempt_id = start_two_sum(menu_env)

    choose(menu_env, Screen("attempt", attempt_id=attempt_id), 1)  # Run tests.

    assert started_flags(menu_env) == [False]


def test_menu_text_leaks_no_technique_hint_or_answer(
    menu_env: MenuEnvironment, problems_dir: Path
) -> None:
    attempt_id = start_two_sum(menu_env)
    screens = [
        MAIN,
        Screen("browse"),
        Screen("browse", words=("two", "sum")),
        Screen("problem", platform="leetcode", problem_id="1"),
        Screen("attempt", attempt_id=attempt_id),
    ]
    package = problems_dir / "leetcode-1"
    withheld = [
        line.strip()
        for name in ("notes.md", "hints/0.md", "hints/1.md", "hints/2.md", "hints/3.md")
        for line in (package / name).read_text(encoding="utf-8").splitlines()
        if len(line.strip()) > 20
    ]
    assert withheld

    for screen in screens:
        menu = build_menu(menu_env, screen)
        text = "\n".join(
            [
                menu.title,
                *menu.lines,
                *(f"{i.label} {i.reason or ''}" for i in menu.items),
            ]
        )
        assert find_technique_terms(text) == [], (screen, text)
        for line in withheld:
            assert line not in text


def test_recommend_screen_offers_the_pick_then_browse_and_main(
    menu_env: MenuEnvironment,
) -> None:
    before = journal_bytes(menu_env)

    menu = build_menu(menu_env, Screen("recommend"))

    assert menu.title == "Recommendation"
    assert keys(menu) == ["start", "browse", "main"]
    assert item(menu, "start").label == "Recommended: Start 1  Two Sum [easy]"
    assert item(menu, "start").problem == ("leetcode", "1")
    assert any("next curriculum objective" in line for line in menu.lines)
    assert journal_bytes(menu_env) == before


def test_choosing_the_recommended_item_starts_that_problem(
    menu_env: MenuEnvironment,
) -> None:
    result = choose(menu_env, Screen("recommend"), 1)

    assert result.code == 0
    assert "Started attempt" in result.stdout
    assert result.next_screen.kind == "attempt"


def test_recommend_screen_with_nothing_ready_says_so(
    menu_env: MenuEnvironment, tmp_path: Path
) -> None:
    empty = MenuEnvironment(
        **{**menu_env.__dict__, "problems_dir": tmp_path / "no-problems"}
    )

    menu = build_menu(empty, Screen("recommend"))

    assert keys(menu) == ["browse", "main"]
    assert any("Nothing to recommend" in line for line in menu.lines)
