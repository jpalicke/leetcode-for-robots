# ABOUTME: Integration tests for the Reviews item in the numbered and terminal menus.
# ABOUTME: Menus run the real CLI against real files and never leak earlier code.

import shutil
from typing import Any

import pytest
from prompt_toolkit.application import create_app_session
from prompt_toolkit.input import create_pipe_input
from prompt_toolkit.output import DummyOutput

from practice.history import attempt_code_path
from practice.journal import Journal
from practice.menu import (
    MAIN,
    CommandResult,
    MenuEnvironment,
    MenuError,
    Screen,
    build_menu,
    choose,
)
from practice.menu_commands import render_menu
from practice.menu_tui import run_tui
from practice.paths import REPO_ROOT
from practice.tutor_policy import find_technique_terms

HASH_MAP = (
    REPO_ROOT / "tests" / "fixtures" / "leetcode_two_sum_solutions" / "hash_map.py"
)
SECRET = "seen = {}"
REVIEWS = Screen("reviews")
ENTER = "\r"
CTRL_C = "\x03"


def records(env: MenuEnvironment) -> list[dict[str, Any]]:
    return Journal(env.practice_dir / "journal.jsonl").read().records


def number_of(menu_env: MenuEnvironment, screen: Screen, key: str) -> int:
    menu = build_menu(menu_env, screen)
    return 1 + next(i for i, item in enumerate(menu.items) if item.key == key)


def run_cli(env: MenuEnvironment, *argv: str) -> CommandResult:
    result = env.run(list(argv))
    assert result.code == 0, result.stdout + result.stderr
    return result


@pytest.fixture
def passed_two_sum(
    menu_env: MenuEnvironment, monkeypatch: pytest.MonkeyPatch
) -> MenuEnvironment:
    """Two Sum passed locally on 2026-11-01. The day is left at that date."""
    monkeypatch.setenv("PRACTICE_NOW", "2026-11-01T09:00:00Z")
    package = menu_env.problems_dir / "leetcode-1"
    started = run_cli(
        menu_env, "attempt", "start", "leetcode", "1", "--package", str(package)
    )
    attempt_id = started.stdout.split()[2]
    code = attempt_code_path(menu_env.practice_dir, "leetcode", "1", attempt_id)
    shutil.copyfile(HASH_MAP, code)
    run_cli(menu_env, "attempt", "test", attempt_id, "--package", str(package))
    return menu_env


def test_the_main_menu_offers_reviews_and_counts_what_is_due(
    passed_two_sum: MenuEnvironment, monkeypatch: pytest.MonkeyPatch
) -> None:
    early = build_menu(passed_two_sum, MAIN)
    monkeypatch.setenv("PRACTICE_NOW", "2026-11-02T09:00:00Z")
    later = build_menu(passed_two_sum, MAIN)

    assert next(i for i in later.items if i.key == "reviews").available
    assert "1 review(s) due." in later.lines
    assert not any("review(s) due" in line for line in early.lines)


def test_the_reviews_screen_lists_due_reviews_and_upcoming_ones(
    passed_two_sum: MenuEnvironment, monkeypatch: pytest.MonkeyPatch
) -> None:
    same_day = build_menu(passed_two_sum, REVIEWS)
    monkeypatch.setenv("PRACTICE_NOW", "2026-11-02T09:00:00Z")
    next_day = build_menu(passed_two_sum, REVIEWS)

    assert [i.key for i in same_day.items] == ["main"]
    assert any("due 2026-11-02" in line for line in same_day.lines)
    assert [i.key for i in next_day.items] == ["review-start", "main"]
    assert next_day.items[0].available


def test_numbered_menu_starts_a_review_like_the_cli_and_leaks_nothing(
    passed_two_sum: MenuEnvironment, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("PRACTICE_NOW", "2026-11-02T09:00:00Z")
    main_menu = number_of(passed_two_sum, MAIN, "reviews")

    opened = choose(passed_two_sum, MAIN, main_menu)
    started = choose(passed_two_sum, opened.next_screen, 1)

    assert opened.next_screen == REVIEWS
    assert started.code == 0
    assert "Started review attempt" in started.stdout
    assert started.next_screen.kind == "attempt"
    last = records(passed_two_sum)[-1]
    assert last["type"] == "attempt_started" and last["review"] is True
    shown = "\n".join(
        [
            started.stdout,
            started.stderr,
            render_menu(build_menu(passed_two_sum, REVIEWS)),
            render_menu(build_menu(passed_two_sum, started.next_screen)),
        ]
    )
    assert SECRET not in shown
    assert find_technique_terms(shown) == []


def test_a_started_review_is_resumed_not_started_twice(
    passed_two_sum: MenuEnvironment, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("PRACTICE_NOW", "2026-11-02T09:00:00Z")
    choose(passed_two_sum, REVIEWS, 1)
    before = records(passed_two_sum)

    menu = build_menu(passed_two_sum, REVIEWS)
    resumed = choose(passed_two_sum, REVIEWS, 1)

    assert [i.key for i in menu.items] == ["review-resume", "main"]
    assert resumed.next_screen.kind == "attempt"
    assert "Resume attempt" in resumed.stdout
    assert records(passed_two_sum) == before


def test_a_review_of_a_problem_without_a_ready_package_cannot_start(
    passed_two_sum: MenuEnvironment, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("PRACTICE_NOW", "2026-11-02T09:00:00Z")
    shutil.rmtree(passed_two_sum.problems_dir / "leetcode-1")
    before = records(passed_two_sum)

    entry = build_menu(passed_two_sum, REVIEWS).items[0]
    result = choose(passed_two_sum, REVIEWS, 1)

    assert not entry.available
    assert result.code != 0
    assert "Nothing was done." in result.stdout
    assert records(passed_two_sum) == before


def test_choosing_a_number_off_the_reviews_screen_is_rejected(
    passed_two_sum: MenuEnvironment,
) -> None:
    with pytest.raises(MenuError, match="choose a number from 1 to 1"):
        choose(passed_two_sum, REVIEWS, 2)


def test_terminal_menu_lists_due_reviews_and_starts_one(
    passed_two_sum: MenuEnvironment,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setenv("PRACTICE_NOW", "2026-11-02T09:00:00Z")
    before = len(records(passed_two_sum))

    # Reviews (item 4), then the first review, then Ctrl-C to leave.
    with create_pipe_input() as pipe:
        with create_app_session(input=pipe, output=DummyOutput()):
            pipe.send_text(f"4{ENTER}1{ENTER}{CTRL_C}")
            code = run_tui(passed_two_sum)

    assert code == 0
    started = records(passed_two_sum)[before:]
    assert [r["type"] for r in started] == ["attempt_started"]
    assert started[0]["review"] is True
    output = capsys.readouterr().out
    assert "Started review attempt" in output
    assert SECRET not in output
