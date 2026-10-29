# ABOUTME: Numbered plain-text front end for the shared menu and its command handler.
# ABOUTME: Stateless: the screen is spelled in flags, and choose N runs the real CLI.

import argparse
import sys
from collections.abc import Callable
from pathlib import Path

from practice.exit_codes import EXIT_BAD_INPUT, EXIT_USAGE
from practice.history import AttemptError
from practice.menu import (
    MAIN,
    CommandResult,
    Menu,
    MenuEnvironment,
    MenuError,
    Screen,
    StepResult,
    build_menu,
    capture_command,
    choose,
)


def make_environment(
    practice_dir: Path,
    catalog_path: Path,
    problems_dir: Path,
    references: Path,
    command: Callable[[list[str]], int],
) -> MenuEnvironment:
    """An environment whose actions run the practice CLI against these folders."""
    shared = [
        "--practice-dir",
        str(practice_dir),
        "--catalog",
        str(catalog_path),
        "--references",
        str(references),
    ]

    def run(argv: list[str]) -> CommandResult:
        return capture_command(command, [*shared, *argv])

    return MenuEnvironment(practice_dir, catalog_path, problems_dir, references, run)


def screen_flags(screen: Screen) -> str:
    """The flags that bring a stateless `practice menu` back to this screen."""
    if screen.kind == "attempt":
        return f" --attempt {screen.attempt_id}"
    if screen.kind == "problem":
        return f" --problem {screen.platform} {screen.problem_id}"
    if screen.kind == "browse":
        return " --browse" + "".join(f" {word}" for word in screen.words)
    return ""


def render_menu(menu: Menu) -> str:
    lines = [menu.title, "=" * len(menu.title), *menu.lines]
    lines.extend(f"Note: {notice}" for notice in menu.notices)
    lines.append("")
    for number, entry in enumerate(menu.items, start=1):
        lines.append(f"  {number}. {entry.label}")
        if not entry.available:
            lines.append(f"       Unavailable: {entry.reason}")
    lines.append("")
    lines.append(f"Choose with: practice menu choose N{screen_flags(menu.screen)}")
    if any(entry.confirm for entry in menu.items):
        lines.append("Reveal items also need --confirm-reveal.")
    return "\n".join(lines)


def screen_from_args(args: argparse.Namespace) -> Screen:
    if args.attempt is not None:
        return Screen("attempt", attempt_id=args.attempt)
    if args.problem is not None:
        platform, problem_id = args.problem
        return Screen("problem", platform=platform, problem_id=problem_id)
    if args.browse is not None:
        return Screen("browse", words=tuple(args.browse))
    return MAIN


def parse_choice(words: list[str]) -> int | None:
    """`choose N` as typed after `menu`; None when nothing was chosen."""
    if not words:
        return None
    if len(words) != 2 or words[0] != "choose" or not words[1].isdecimal():
        raise MenuError("use: practice menu choose N")
    return int(words[1])


def show_step(step: StepResult) -> None:
    if step.stdout:
        print(step.stdout.rstrip("\n"))
        print()
    if step.stderr:
        print(step.stderr.rstrip("\n"), file=sys.stderr)


def run_menu_command(args: argparse.Namespace, env: MenuEnvironment) -> int:
    try:
        number = parse_choice(args.steps)
        screen = screen_from_args(args)
        code = 0
        if number is not None:
            step = choose(env, screen, number, confirmed=args.confirm_reveal)
            show_step(step)
            screen, code = step.next_screen, step.code
        print(render_menu(build_menu(env, screen)))
        return code
    except MenuError as error:
        print(f"practice: error: {error}", file=sys.stderr)
        return EXIT_USAGE
    except AttemptError as error:
        print(f"practice: error: {error}", file=sys.stderr)
        return EXIT_BAD_INPUT
