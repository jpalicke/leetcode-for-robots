# ABOUTME: Integration tests for the Recommendation item in the numbered and TUI menus.
# ABOUTME: Real journal, catalog and CLI; showing a pick never writes anything.

import shutil
from typing import Any

import pytest
from prompt_toolkit.application import create_app_session
from prompt_toolkit.input import create_pipe_input
from prompt_toolkit.output import DummyOutput

from practice.history import attempt_code_path
from practice.journal import Journal
from practice.menu import MAIN, MenuEnvironment, Screen, build_menu, choose
from practice.menu_commands import render_menu
from practice.menu_tui import run_tui
from practice.paths import REPO_ROOT
from practice.tutor_policy import find_technique_terms

HASH_MAP = (
    REPO_ROOT / "tests" / "fixtures" / "leetcode_two_sum_solutions" / "hash_map.py"
)
SECRET = "seen = {}"
RECOMMEND = Screen("recommend")
ENTER = "\r"
CTRL_C = "\x03"


def records(env: MenuEnvironment) -> list[dict[str, Any]]:
    return Journal(env.practice_dir / "journal.jsonl").read().records


def number_of(env: MenuEnvironment, screen: Screen, key: str) -> int:
    menu = build_menu(env, screen)
    return 1 + next(i for i, item in enumerate(menu.items) if item.key == key)


@pytest.fixture(autouse=True)
def fixed_day(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("PRACTICE_NOW", "2026-11-01T09:00:00Z")


def test_the_recommend_screen_explains_the_pick_without_writing(
    menu_env: MenuEnvironment,
) -> None:
    menu = build_menu(menu_env, RECOMMEND)
    shown = render_menu(menu)

    assert "Recommended next:" in shown
    assert "Two Sum [easy]" in shown
    assert "next curriculum objective" in shown
    assert "Evidence: No attempts yet." in shown
    assert [i.key for i in menu.items][-2:] == ["browse", "main"]
    assert not (menu_env.practice_dir / "journal.jsonl").exists()
    assert find_technique_terms(shown) == []


def test_choosing_the_recommendation_starts_it_like_the_cli(
    menu_env: MenuEnvironment,
) -> None:
    main_item = number_of(menu_env, MAIN, "recommendations")

    opened = choose(menu_env, MAIN, main_item)
    started = choose(menu_env, opened.next_screen, 1)

    assert opened.next_screen == RECOMMEND
    assert started.code == 0
    assert "Started attempt" in started.stdout
    assert [r["type"] for r in records(menu_env)] == ["attempt_started"]
    assert records(menu_env)[0]["problem_id"] == "1"


def test_a_due_review_is_offered_and_started_as_a_review(
    menu_env: MenuEnvironment, monkeypatch: pytest.MonkeyPatch
) -> None:
    package = menu_env.problems_dir / "leetcode-1"
    started = menu_env.run(
        ["attempt", "start", "leetcode", "1", "--package", str(package)]
    )
    attempt_id = started.stdout.split()[2]
    shutil.copyfile(
        HASH_MAP, attempt_code_path(menu_env.practice_dir, "leetcode", "1", attempt_id)
    )
    menu_env.run(["attempt", "test", attempt_id, "--package", str(package)])
    monkeypatch.setenv("PRACTICE_NOW", "2026-11-02T09:00:00Z")
    before = records(menu_env)

    menu = build_menu(menu_env, RECOMMEND)
    shown = render_menu(menu)

    assert menu.items[0].key == "review-start"
    assert "due review" in shown
    assert records(menu_env) == before
    result = choose(menu_env, RECOMMEND, 1)
    assert "Started review attempt" in result.stdout
    assert SECRET not in shown + result.stdout
    assert find_technique_terms(shown) == []


def test_terminal_menu_shows_the_recommendation_and_starts_it(
    menu_env: MenuEnvironment, capsys: pytest.CaptureFixture[str]
) -> None:
    item = number_of(menu_env, MAIN, "recommendations")

    with create_pipe_input() as pipe:
        with create_app_session(input=pipe, output=DummyOutput()):
            pipe.send_text(f"{item}{ENTER}1{ENTER}{CTRL_C}")
            code = run_tui(menu_env)

    assert code == 0
    assert [r["type"] for r in records(menu_env)] == ["attempt_started"]
    output = capsys.readouterr().out
    assert "Started attempt" in output
    assert find_technique_terms(output) == []


def test_terminal_menu_browsing_the_recommendation_writes_nothing(
    menu_env: MenuEnvironment,
) -> None:
    item = number_of(menu_env, MAIN, "recommendations")

    with create_pipe_input() as pipe:
        with create_app_session(input=pipe, output=DummyOutput()):
            pipe.send_text(f"{item}{ENTER}{CTRL_C}")
            code = run_tui(menu_env)

    assert code == 0
    assert not (menu_env.practice_dir / "journal.jsonl").exists()
