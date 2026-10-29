# ABOUTME: The `practice recommend` command: one primary pick, a few alternatives.
# ABOUTME: Read-only. It prints the command to start a pick and never starts one.

import argparse
import json
import sys
from pathlib import Path

from practice import clock
from practice.catalog import CatalogError, load_catalog
from practice.curriculum import CurriculumError, load_curriculum
from practice.exercises import exercise_status
from practice.exit_codes import EXIT_BAD_INPUT, EXIT_USAGE
from practice.journal import JournalError
from practice.recommendations import Candidate, Recommendation, build_recommendation


def run_recommend_command(args: argparse.Namespace, practice_dir: Path) -> int:
    try:
        result = _recommend(args, practice_dir)
    except clock.ClockError as error:
        print(f"practice: error: {error}", file=sys.stderr)
        return EXIT_USAGE
    except (CatalogError, CurriculumError, JournalError) as error:
        print(f"practice: error: {error}", file=sys.stderr)
        return EXIT_BAD_INPUT
    if args.choose is not None:
        return _show_choice(result, args.choose, args.json)
    if args.json:
        print(json.dumps(_to_dict(result), indent=2))
    else:
        print(render_recommendation(result))
    return 0  # Having nothing to recommend is an answer, not a failure.


def _recommend(args: argparse.Namespace, practice_dir: Path) -> Recommendation:
    catalog = load_catalog(args.catalog)
    curriculum = load_curriculum(args.curriculum, catalog)

    def ready(platform: str, problem_id: str) -> bool:
        return exercise_status(
            args.problems_dir, args.references, platform, problem_id
        ).ready

    return build_recommendation(practice_dir, catalog, curriculum, ready, clock.today())


def _to_dict(result: Recommendation) -> dict[str, object]:
    primary = result.primary
    return {
        "primary": primary.to_dict() if primary else None,
        "alternatives": [c.to_dict() for c in result.alternatives],
        "pending": result.pending,
        "message": result.message,
    }


def describe_candidate(candidate: Candidate) -> list[str]:
    """The lines that explain one pick: label, plain reason, evidence, how to start."""
    return [
        f"{candidate.problem_id}  {candidate.label}",
        f"  Why: {candidate.reason_phrase}. {candidate.detail}",
        f"  Evidence: {candidate.evidence.text}",
        f"  To {candidate.action} it: {candidate.command}",
    ]


def render_recommendation(result: Recommendation) -> str:
    if result.primary is None:
        return result.message
    lines = ["Recommended next:", *describe_candidate(result.primary)]
    if result.alternatives:
        lines.append("")
        lines.append("Other options:")
        for number, candidate in enumerate(result.alternatives, start=2):
            lines.append(f"  {number}. {candidate.problem_id}  {candidate.label}")
            lines.append(f"     Why: {candidate.reason_phrase}. {candidate.detail}")
            lines.append(f"     Evidence: {candidate.evidence.text}")
        lines.append("")
        lines.append("See one in full with: practice recommend --choose N")
    if result.pending:
        lines.append(
            f"{result.pending} curriculum problem(s) are waiting for ready exercises."
        )
    lines.append("You can always start any other problem: practice search WORDS")
    return "\n".join(lines)


def _show_choice(result: Recommendation, number: int, as_json: bool) -> int:
    """Show the Nth pick (1 is the primary). It starts nothing: you run the command."""
    if not 1 <= number <= len(result.candidates):
        count = len(result.candidates)
        problem = (
            f"choose a number from 1 to {count}, not {number}"
            if count
            else f"there is nothing to choose. {result.message}"
        )
        print(f"practice: error: {problem}", file=sys.stderr)
        return EXIT_USAGE
    chosen = result.candidates[number - 1]
    if as_json:
        print(json.dumps(chosen.to_dict(), indent=2))
    else:
        print("You chose:")
        print("\n".join(describe_candidate(chosen)))
        print("Nothing was started or recorded. Run the command above when ready.")
    return 0
