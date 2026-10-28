# ABOUTME: Command handlers for `practice tutor`: check, start and classes.
# ABOUTME: Exit codes follow the rest of the tool: 0 ok, 3 contract problems found.

import argparse
import sys
from pathlib import Path

from practice.exit_codes import EXIT_BAD_INPUT
from practice.history import (
    STATUS_LABELS,
    Attempt,
    History,
    latest_unfinished,
    load_history,
    view_attempt,
)
from practice.journal import JournalError
from practice.tutor_policy import (
    POLICY_PATH,
    REQUIRED_RULE_IDS,
    check_contract,
    render_class_lines,
)


def run_tutor_command(
    args: argparse.Namespace, practice_dir: Path, repo_root: Path
) -> int:
    if args.tutor_command == "classes":
        print("\n".join(render_class_lines()))
        return 0
    if args.tutor_command == "check":
        return _check(args.root or repo_root)
    try:
        return _start(practice_dir)
    except JournalError as error:
        print(f"practice: error: {error}", file=sys.stderr)
        return EXIT_BAD_INPUT


def _check(root: Path) -> int:
    problems = check_contract(root)
    for problem in problems:
        print(f"practice: error: {problem}", file=sys.stderr)
    if problems:
        print(f"Tutor contract has {len(problems)} problem(s).", file=sys.stderr)
        return EXIT_BAD_INPUT
    print(f"Tutor contract ok: {len(REQUIRED_RULE_IDS)} rules in {POLICY_PATH}.")
    return 0


def _start(practice_dir: Path) -> int:
    history = load_history(practice_dir)
    for notice in history.notices:
        print(f"practice: warning: {notice}", file=sys.stderr)
    print("\n".join(briefing(history, practice_dir)))
    return 0


def briefing(history: History, practice_dir: Path) -> list[str]:
    """Session context that is safe to read: settings and counts, never private text."""
    lines = [
        "Practice session briefing",
        f"Policy: read {POLICY_PATH} now and follow it for the whole session.",
    ]
    attempt = latest_unfinished(history, None, None)
    if attempt is None:
        lines += [
            "Mode: practice (default)",
            "Timing: untimed (default)",
            "No unfinished attempt. Study mode and timed practice happen only when "
            "the learner starts an attempt with --mode study or --timed.",
        ]
    else:
        lines += _attempt_lines(attempt, history, practice_dir)
    lines.append(
        "Not printed on purpose: attempt code, notes, assistance summaries and "
        "earlier attempts. Ask the learner before reading any of them."
    )
    return lines


def _attempt_lines(attempt: Attempt, history: History, practice_dir: Path) -> list[str]:
    view = view_attempt(attempt, practice_dir)
    timing = "timed (chosen when the attempt started)" if attempt.timed else "untimed"
    lines = [
        f"Active attempt: {attempt.attempt_id}",
        f"Problem: {attempt.platform} {attempt.problem_id}  {attempt.title} "
        f"({attempt.language})",
        f"Mode: {attempt.mode}",
        f"Timing: {timing}",
        f"Status: {STATUS_LABELS[view.status]}",
        f"Code file: {view.code_path}",
    ]
    if view.latest_run is not None:
        lines.append(f"Last test run: {view.latest_run['status']}")
    lines.append(_assistance_line(attempt))
    lines.append(
        f"Record delivered help with: uv run --locked practice attempt "
        f"note-assistance {attempt.attempt_id} --kind hint --level N"
    )
    return lines


def _assistance_line(attempt: Attempt) -> str:
    events = [e for e in attempt.events if e.get("type") == "assistance"]
    if not events:
        return "Assistance recorded: none"
    count = len(events)
    text = f"Assistance recorded: {count} event{'s' if count != 1 else ''}"
    levels = [
        e["level"]
        for e in events
        if e.get("kind") == "hint" and e.get("level") is not None
    ]
    if levels:
        text += f", highest hint level {max(levels)}"
    return text
