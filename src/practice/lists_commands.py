# ABOUTME: Handles `practice lists`: browse curated problem lists with their status.
# ABOUTME: Read-only; a bad list file refuses every command and prints nothing else.

import argparse
import json
import sys

from practice.catalog import CatalogError, load_catalog
from practice.exercises import Exercise
from practice.exit_codes import EXIT_BAD_INPUT, EXIT_NOT_PASSED
from practice.lists import (
    ListError,
    ProblemList,
    ProblemStatus,
    count_statuses,
    list_statuses,
    load_lists,
)

TAG_WIDTH = 9


def run_lists_command(args: argparse.Namespace) -> int:
    try:
        catalog = load_catalog(args.catalog)
        lists = load_lists(args.lists_dir, catalog)
    except (CatalogError, ListError) as error:
        print(f"practice: error: {error}", file=sys.stderr)
        return EXIT_BAD_INPUT
    if args.lists_command == "check":
        report = {"valid": True, "lists": len(lists)}
        print(json.dumps(report) if args.json else f"{len(lists)} lists valid.")
        return 0
    if args.lists_command == "show":
        return _show(args, lists)
    return _summary(args, lists, catalog.fetched_on)


def _summary(
    args: argparse.Namespace, lists: tuple[ProblemList, ...], fetched_on: str
) -> int:
    if not lists:
        print(f"No lists found in {args.lists_dir}.")
        return 0
    cache: dict[int, Exercise] = {}
    rows = []
    for item in lists:
        statuses = list_statuses(item, args.problems_dir, args.references, cache)
        rows.append((item, count_statuses(statuses)))
    if args.json:
        print(
            json.dumps(
                [
                    {
                        "id": item.list_id,
                        "name": item.name,
                        "size": item.size,
                        "groups": len(item.groups),
                        "counts": counts,
                    }
                    for item, counts in rows
                ],
                indent=2,
            )
        )
        return 0
    print(f"Problem lists (catalog snapshot {fetched_on})")
    width = max(len(item.list_id) for item in lists)
    name_width = max(len(item.name) for item in lists)
    print(f"{'id':<{width}}  {'name':<{name_width}}  size  ready  blocked  pending")
    for item, counts in rows:
        print(
            f"{item.list_id:<{width}}  {item.name:<{name_width}}  {item.size:>4}  "
            f"{counts['ready']:>5}  {counts['blocked']:>7}  {counts['pending']:>7}"
        )
    print("Open one with: practice lists show ID")
    return 0


def _show(args: argparse.Namespace, lists: tuple[ProblemList, ...]) -> int:
    chosen = next((item for item in lists if item.list_id == args.list_id), None)
    if chosen is None:
        known = ", ".join(item.list_id for item in lists) or "none"
        print(
            f"practice: error: no list named {args.list_id!r}. Known lists: {known}",
            file=sys.stderr,
        )
        return EXIT_NOT_PASSED
    statuses = list_statuses(chosen, args.problems_dir, args.references)
    counts = count_statuses(statuses)
    by_id = {s.problem.frontend_question_id: s for s in statuses}
    if args.json:
        print(json.dumps(_to_dict(chosen, counts, by_id), indent=2))
        return 0
    source = chosen.source
    print(
        f"{chosen.name} ({chosen.size} problems: {counts['ready']} ready, "
        f"{counts['blocked']} blocked, {counts['pending']} pending)"
    )
    retrieved = source["retrieved_on"]
    print(f"Source: {source['kind']}, {source['url']} (retrieved {retrieved})")
    for group in chosen.groups:
        print(f"\n{group.name}")
        for problem in group.problems:
            status = by_id[problem.frontend_question_id]
            tag = f"[{status.status}]"
            premium = "  premium" if status.status == "blocked" else ""
            print(
                f"  {tag:<{TAG_WIDTH}} {problem.frontend_question_id:>5}  "
                f"{problem.title}  ({problem.difficulty}){premium}"
            )
    return 0


def _to_dict(
    chosen: ProblemList, counts: dict[str, int], by_id: dict[int, ProblemStatus]
) -> dict[str, object]:
    return {
        "id": chosen.list_id,
        "name": chosen.name,
        "platform": chosen.platform,
        "size": chosen.size,
        "source": chosen.source,
        "counts": counts,
        "groups": [
            {
                "name": group.name,
                "problems": [
                    {
                        "id": p.frontend_question_id,
                        "slug": p.slug,
                        "title": p.title,
                        "difficulty": p.difficulty,
                        "paid_only": p.paid_only,
                        "status": by_id[p.frontend_question_id].status,
                        "reason": by_id[p.frontend_question_id].reason,
                    }
                    for p in group.problems
                ],
            }
            for group in chosen.groups
        ],
    }
