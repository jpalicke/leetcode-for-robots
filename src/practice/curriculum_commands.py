# ABOUTME: Handles read-only curriculum validation and learner-safe objective listing.
# ABOUTME: Reports invalid files with exit 3 and never opens private learner state.

import argparse
import json
import sys

from practice.catalog import CatalogError, load_catalog
from practice.curriculum import CurriculumError, load_curriculum
from practice.exit_codes import EXIT_BAD_INPUT


def run_curriculum_command(args: argparse.Namespace) -> int:
    try:
        curriculum = load_curriculum(args.file, load_catalog(args.catalog))
    except (CatalogError, CurriculumError) as error:
        print(f"practice: error: {error}", file=sys.stderr)
        return EXIT_BAD_INPUT
    if args.curriculum_command == "check":
        report = {
            "valid": True,
            "objectives": len(curriculum.concepts),
            "problems": len(curriculum.starters),
        }
        print(json.dumps(report, indent=2) if args.json else "Curriculum valid.")
    else:
        objectives = curriculum.next_objectives()
        if args.json:
            print(json.dumps([o.to_dict() for o in objectives], indent=2))
        else:
            for objective in objectives:
                print(objective.label)
                for problem in objective.problems:
                    print(
                        f"  {problem.platform}/{problem.frontend_question_id}: "
                        f"{problem.title}"
                    )
    return 0
