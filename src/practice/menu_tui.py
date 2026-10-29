# ABOUTME: Interactive arrow-key terminal menu; the only module using prompt_toolkit.
# ABOUTME: It drives the shared menu core, so it always agrees with the numbered menu.

import sys

from prompt_toolkit.shortcuts import choice, confirm

from practice.exit_codes import EXIT_USAGE
from practice.history import AttemptError
from practice.menu import (
    MAIN,
    Item,
    MenuEnvironment,
    MenuError,
    build_menu,
    choose,
)
from practice.menu_commands import show_step

NOT_A_TERMINAL = (
    "practice: error: the interactive menu needs a terminal. "
    "Use the numbered menu instead: practice menu"
)
QUIT = "quit"


def stdio_is_terminal() -> bool:
    return sys.stdin.isatty() and sys.stdout.isatty()


def label(item: Item) -> str:
    return item.label if item.available else f"{item.label} (unavailable)"


def run_tui(env: MenuEnvironment) -> int:
    """Loop over menus until the learner quits. Returns an exit code."""
    screen = MAIN
    while True:
        try:
            menu = build_menu(env, screen)
        except (MenuError, AttemptError) as error:
            print(f"practice: error: {error}", file=sys.stderr)
            return EXIT_USAGE
        print()
        print(menu.title)
        for line in (*menu.lines, *(f"Note: {n}" for n in menu.notices)):
            print(line)
        options: list[tuple[int | str, str]] = [
            (number, label(item)) for number, item in enumerate(menu.items, start=1)
        ]
        options.append((QUIT, "Quit"))
        try:
            picked = choice("Choose an item", options=options)
        except (KeyboardInterrupt, EOFError):
            return 0
        if picked == QUIT:
            return 0
        assert isinstance(picked, int)
        item = menu.items[picked - 1]
        confirmed = False
        if item.available and item.confirm:
            try:
                confirmed = confirm("This reveals the full solution. Continue?")
            except (KeyboardInterrupt, EOFError):
                continue
        try:
            step = choose(env, screen, picked, confirmed=confirmed)
        except (MenuError, AttemptError) as error:
            print(f"practice: error: {error}", file=sys.stderr)
            continue
        show_step(step)
        screen = step.next_screen
