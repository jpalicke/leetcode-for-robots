# ABOUTME: Integration tests: menu actions and the plain CLI leave identical journals.
# ABOUTME: Real files in temp folders, the real CLI, and the terminal menu on a pipe.

import shutil
from pathlib import Path
from typing import Any

import pytest
from prompt_toolkit.application import create_app_session
from prompt_toolkit.input import create_pipe_input
from prompt_toolkit.output import DummyOutput

from practice.catalog import DEFAULT_CATALOG_PATH
from practice.cli import main
from practice.journal import Journal
from practice.menu import MAIN, MenuEnvironment, Screen, build_menu, choose
from practice.menu_commands import make_environment
from practice.menu_tui import run_tui
from practice.paths import REFERENCES_DIR

HASH_MAP_SOLUTION = (
    Path(__file__).resolve().parents[1]
    / "fixtures"
    / "leetcode_two_sum_solutions"
    / "hash_map.py"
)
ENTER = "\r"
DOWN = "\x1b[B"
CTRL_C = "\x03"


def records(practice_dir: Path) -> list[dict[str, Any]]:
    return Journal(practice_dir / "journal.jsonl").read().records


def shape(record: dict[str, Any]) -> dict[str, Any]:
    """A record without the fields that differ between any two runs."""
    volatile = {"event_id", "at", "attempt_id", "run_id", "duration_seconds", "run_at"}
    return {
        k: v.rsplit("/", 2)[0] if k == "code_path" else v
        for k, v in record.items()
        if k not in volatile
    }


def number_of(env: MenuEnvironment, screen: Screen, key: str) -> int:
    return [item.key for item in build_menu(env, screen).items].index(key) + 1


def direct(env: MenuEnvironment, *argv: str) -> int:
    return env.run(list(argv)).code


def second_environment(tmp_path: Path, problems_dir: Path) -> MenuEnvironment:
    return make_environment(
        tmp_path / "direct", DEFAULT_CATALOG_PATH, problems_dir, REFERENCES_DIR, main
    )


def test_menu_start_and_test_match_the_direct_cli_journal(
    menu_env: MenuEnvironment,
    problems_dir: Path,
    tmp_path: Path,
) -> None:
    plain = second_environment(tmp_path, problems_dir)
    package = str(problems_dir / "leetcode-1")

    problem = Screen("problem", platform="leetcode", problem_id="1")
    started = choose(menu_env, problem, number_of(menu_env, problem, "start"))
    assert started.code == 0, started.stderr
    assert direct(plain, "attempt", "start", "leetcode", "1", "--package", package) == 0

    menu_attempt = started.next_screen
    plain_attempt = plain.run(["attempt", "resume"]).stdout.split()[2]
    for env, attempt_id in (
        (menu_env, menu_attempt.attempt_id),
        (plain, plain_attempt),
    ):
        code = env.practice_dir / "attempts" / "leetcode-1" / attempt_id
        target = next(code.glob("*.py"))
        shutil.copyfile(HASH_MAP_SOLUTION, target)

    ran = choose(menu_env, menu_attempt, number_of(menu_env, menu_attempt, "test"))
    assert ran.code == 0, ran.stdout + ran.stderr
    assert direct(plain, "attempt", "test", plain_attempt, "--package", package) == 0

    menu_records = [shape(r) for r in records(menu_env.practice_dir)]
    plain_records = [shape(r) for r in records(plain.practice_dir)]
    assert menu_records == plain_records
    assert [r["type"] for r in menu_records] == ["attempt_started", "test_run"]


def test_menu_hint_request_matches_the_cli_and_records_no_assistance(
    menu_env: MenuEnvironment,
) -> None:
    problem = Screen("problem", platform="leetcode", problem_id="1")
    started = choose(menu_env, problem, number_of(menu_env, problem, "start"))
    screen = started.next_screen
    before = records(menu_env.practice_dir)

    hint = choose(menu_env, screen, number_of(menu_env, screen, "hint"))

    assert hint.code == 0, hint.stderr
    assert "Action: hint" in hint.stdout
    assert records(menu_env.practice_dir) == before
    assert not any(r["type"] == "assistance" for r in records(menu_env.practice_dir))


def test_attempts_started_before_the_menu_existed_are_preserved(
    menu_env: MenuEnvironment, problems_dir: Path
) -> None:
    package = str(problems_dir / "leetcode-1")
    assert (
        direct(menu_env, "attempt", "start", "leetcode", "1", "--package", package) == 0
    )
    before = menu_env.practice_dir.joinpath("journal.jsonl").read_bytes()

    menu = build_menu(menu_env, MAIN)

    assert menu.items[0].available
    assert menu_env.practice_dir.joinpath("journal.jsonl").read_bytes() == before


def tui_flow(env: MenuEnvironment, keystrokes: str) -> int:
    with create_pipe_input() as pipe:
        with create_app_session(input=pipe, output=DummyOutput()):
            pipe.send_text(keystrokes)
            return run_tui(env)


def test_terminal_menu_starts_and_tests_an_attempt_like_the_numbered_menu(
    menu_env: MenuEnvironment, capsys: pytest.CaptureFixture[str]
) -> None:
    # Browse, Two Sum, start, run tests, then Ctrl-C to leave.
    code = tui_flow(menu_env, f"2{ENTER}1{ENTER}1{ENTER}1{ENTER}{CTRL_C}")

    assert code == 0
    types = [r["type"] for r in records(menu_env.practice_dir)]
    assert types[0] == "attempt_started"
    assert len(types) >= 2
    assert "Started attempt" in capsys.readouterr().out


def test_terminal_menu_timed_item_opts_in_for_one_attempt_only(
    menu_env: MenuEnvironment, capsys: pytest.CaptureFixture[str]
) -> None:
    # Item 7 is timed practice: pick a problem, then the timed start (item 1).
    code = tui_flow(menu_env, f"7{ENTER}1{ENTER}1{ENTER}{CTRL_C}")

    assert code == 0
    started = [
        r for r in records(menu_env.practice_dir) if r["type"] == "attempt_started"
    ]
    assert [r["timed"] for r in started] == [True]
    assert "Timer started" in capsys.readouterr().out


def test_terminal_menu_study_item_starts_a_study_mode_attempt(
    menu_env: MenuEnvironment, capsys: pytest.CaptureFixture[str]
) -> None:
    # Item 6 is study mode: pick the problem, then leave with Ctrl-C.
    code = tui_flow(menu_env, f"6{ENTER}1{ENTER}{CTRL_C}")

    assert code == 0
    started = [
        r for r in records(menu_env.practice_dir) if r["type"] == "attempt_started"
    ]
    assert [r["mode"] for r in started] == ["study"]
    output = capsys.readouterr().out
    assert "Paste-ready request for the tutor:" in output
    assert "practice knowledge export leetcode 1 --mode study" in output
