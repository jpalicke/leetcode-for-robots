# ABOUTME: Plans which ticket each catalog problem belongs to, and reports coverage.
# ABOUTME: Offline and deterministic; it never talks to GitHub or creates a ticket.

import argparse
import json
import math
import os
import sys
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from practice.catalog import Catalog, CatalogError, Entry, load_catalog
from practice.exercises import exercise_status
from practice.lists import ListError, load_lists
from practice.paths import REFERENCES_DIR, REPO_ROOT
from practice.topics import TopicsError, load_topics

DEFAULT_CATALOG = REPO_ROOT / "catalog" / "leetcode.json"
DEFAULT_TOPICS = REPO_ROOT / "catalog" / "leetcode-topics.json"
DEFAULT_RULES = REPO_ROOT / "catalog" / "class-rules.json"
DEFAULT_PLAN = REPO_ROOT / "catalog" / "ticket-plan.json"
DEFAULT_CURRICULUM = REPO_ROOT / "curriculum" / "core.json"
DEFAULT_LISTS = REPO_ROOT / "catalog" / "lists"
DEFAULT_PROBLEMS = REPO_ROOT / "problems"
DIFFICULTIES = ("easy", "medium", "hard")
STATUSES = ("ready", "in_progress", "blocked", "pending")
PLAN_STATUSES = ("pending", "in_progress", "blocked")
CLASS_KEYS = (
    "id",
    "kind",
    "title",
    "rule",
    "difficulty",
    "status",
    "reason",
    "note",
    "issue",
    "entries",
    "removed",
)
RULES_KEYS = {
    "schema_version",
    "ticket_size",
    "individual",
    "specialized",
    "ignored_tags",
    "ignored_tags_note",
    "concepts",
    "fallback",
}
READINESS_BAR = (
    "A problem is ready when it has a verified statement, signature and output "
    "contract; a blank typed starter; a local cited reference (a published one "
    "preferred) with its notices preserved and any adapters kept separate; gradual "
    "classified hints; realistic tests; and independent correctness evidence from "
    "running them. Empty suites, stubs, exceptions and timeouts never count. Local "
    "validation and LeetCode acceptance stay separate."
)


class ToolError(Exception):
    """An input is missing or inconsistent; exit 1."""


@dataclass(frozen=True)
class Specialized:
    rule_id: str
    title: str
    reason: str
    premium: bool
    categories: frozenset[str]
    topics: frozenset[str]


@dataclass(frozen=True)
class Concept:
    concept_id: str
    tags: frozenset[str]
    note: str


@dataclass(frozen=True)
class Rules:
    ticket_size: int
    individual: dict[int, int]  # Problem number to its existing issue.
    specialized: tuple[Specialized, ...]
    ignored_tags: frozenset[str]
    concepts: tuple[Concept, ...]
    fallback_id: str
    fallback_title: str
    fallback_note: str
    fallback_split: bool


@dataclass(frozen=True)
class Curriculum:
    names: dict[str, str]
    prerequisites: dict[str, list[str]]
    order: list[str]


@dataclass
class Ticket:
    ticket_id: str
    kind: str  # "individual" or "class".
    rule: str
    difficulty: str | None
    status: str
    reason: str
    note: str
    issue: int | None
    entries: list[int] = field(default_factory=list)
    removed: list[int] = field(default_factory=list)
    title: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.ticket_id,
            "kind": self.kind,
            "title": self.title,
            "rule": self.rule,
            "difficulty": self.difficulty,
            "status": self.status,
            "reason": self.reason,
            "note": self.note,
            "issue": self.issue,
            "entries": self.entries,
            "removed": self.removed,
        }


def read_json(path: Path, what: str) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError) as error:
        raise ToolError(f"cannot read the {what} {path}: {error}") from error
    except json.JSONDecodeError as error:
        raise ToolError(f"the {what} {path} is not valid JSON: {error}") from error


def load_rules(path: Path, curriculum: Curriculum) -> Rules:
    raw = read_json(path, "rules file")
    where = f"the rules file {path.name}"
    try:
        if not isinstance(raw, dict) or set(raw) - RULES_KEYS:
            raise ToolError(f"{where} has unknown or missing top-level keys")
        if raw["schema_version"] != 1:
            raise ToolError(f"{where}: schema_version must be 1")
        size = raw["ticket_size"]
        if isinstance(size, bool) or not isinstance(size, int) or size < 1:
            raise ToolError(f"{where}: ticket_size must be a positive whole number")
        individual = {int(r["problem"]): int(r["issue"]) for r in raw["individual"]}
        specialized = tuple(_specialized(item) for item in raw["specialized"])
        ids = [s.rule_id for s in specialized]
        if len(ids) != len(set(ids)):
            raise ToolError(f"{where}: a specialized rule id is repeated")
        ignored = frozenset(str(tag) for tag in raw["ignored_tags"])
        concepts = tuple(
            Concept(str(c["id"]), frozenset(c["tags"]), str(c.get("note", "")))
            for c in raw["concepts"]
        )
        fallback = raw["fallback"]
        rules = Rules(
            size,
            individual,
            specialized,
            ignored,
            concepts,
            str(fallback["id"]),
            str(fallback["title"]),
            str(fallback.get("note", "")),
            bool(fallback["split_by_difficulty"]),
        )
    except (KeyError, TypeError, ValueError, AttributeError) as error:
        raise ToolError(f"{where} is invalid ({error!r})") from error
    seen: dict[str, str] = {}
    for concept in rules.concepts:
        if concept.concept_id not in curriculum.names:
            raise ToolError(
                f"{where}: the concept {concept.concept_id!r} is not in the curriculum"
            )
        for tag in sorted(concept.tags):
            if tag in seen:
                raise ToolError(
                    f"{where}: the topic tag {tag!r} is in more than one concept "
                    f"({seen[tag]} and {concept.concept_id})"
                )
            seen[tag] = concept.concept_id
    both = sorted(set(seen) & rules.ignored_tags)
    if both:
        raise ToolError(f"{where}: {both[0]!r} is both mapped to a concept and ignored")
    return rules


def _specialized(item: dict[str, Any]) -> Specialized:
    match = item["match"]
    if set(match) - {"premium", "categories", "topics"}:
        raise ToolError(f"the rule {item['id']!r} has an unknown match key")
    return Specialized(
        str(item["id"]),
        str(item["title"]),
        str(item["reason"]),
        bool(match.get("premium", False)),
        frozenset(match.get("categories", [])),
        frozenset(match.get("topics", [])),
    )


def load_curriculum_names(path: Path) -> Curriculum:
    raw = read_json(path, "curriculum")
    try:
        concepts = raw["concepts"]
        return Curriculum(
            {c["id"]: c["name"] for c in concepts},
            {c["id"]: list(c["prerequisites"]) for c in concepts},
            [c["id"] for c in concepts],
        )
    except (KeyError, TypeError) as error:
        raise ToolError(f"the curriculum {path} is invalid ({error!r})") from error


@dataclass(frozen=True)
class Inputs:
    catalog: Catalog
    facts: dict[int, tuple[frozenset[str], frozenset[str]]]
    topics_fetched_on: str
    rules: Rules
    curriculum: Curriculum


def load_inputs(args: argparse.Namespace) -> Inputs:
    try:
        catalog = load_catalog(args.catalog)
        topics = load_topics(args.topics, catalog)
    except (CatalogError, TopicsError) as error:
        raise ToolError(str(error)) from error
    curriculum = load_curriculum_names(args.curriculum)
    rules = load_rules(args.rules, curriculum)
    facts = {
        number: (frozenset(f.categories), frozenset(f.topics))
        for number, f in topics.facts.items()
    }
    used = {tag for _, tags in facts.values() for tag in tags}
    mapped = {tag for c in rules.concepts for tag in c.tags}
    unmapped = sorted(used - mapped - rules.ignored_tags)
    if unmapped:
        shown = ", ".join(unmapped[:8]) + (" ..." if len(unmapped) > 8 else "")
        raise ToolError(
            f"{len(unmapped)} topic tag(s) are not in the rules, so no concept is "
            f"decided for them: {shown}. Add each to a concept or to ignored_tags "
            f"in {args.rules.name}."
        )
    return Inputs(catalog, facts, topics.fetched_on, rules, curriculum)


def group_of(entry: Entry, inputs: Inputs) -> tuple[str, str | None]:
    """The rule that places this problem and, for concept classes, its difficulty."""
    rules = inputs.rules
    number = entry.frontend_question_id
    if number in rules.individual:
        return f"problem-{number}", None
    categories, topics = inputs.facts[number]
    for rule in rules.specialized:
        if (
            (rule.premium and entry.paid_only)
            or rule.categories & categories
            or rule.topics & topics
        ):
            return rule.rule_id, None
    for concept in rules.concepts:
        if concept.tags & topics:
            return concept.concept_id, entry.difficulty
    return rules.fallback_id, (entry.difficulty if rules.fallback_split else None)


def prefix_of(group: str, difficulty: str | None) -> str:
    return f"{group}-{difficulty}" if difficulty else group


def read_plan(path: Path) -> list[Ticket]:
    raw = read_json(path, "plan")
    try:
        if raw["schema_version"] != 1:
            raise ToolError(f"the plan {path.name}: schema_version must be 1")
        tickets = []
        for item in raw["classes"]:
            if item["status"] not in PLAN_STATUSES:
                raise ToolError(f"the plan {path.name}: bad status {item['status']!r}")
            tickets.append(
                Ticket(
                    str(item["id"]),
                    str(item["kind"]),
                    str(item["rule"]),
                    item["difficulty"],
                    str(item["status"]),
                    str(item["reason"]),
                    str(item.get("note", "")),
                    item["issue"],
                    [int(n) for n in item["entries"]],
                    [int(n) for n in item["removed"]],
                    str(item["title"]),
                )
            )
    except (KeyError, TypeError, ValueError) as error:
        raise ToolError(f"the plan {path.name} is invalid ({error!r})") from error
    return tickets


@dataclass
class Outcome:
    tickets: list[Ticket]
    placed: list[int] = field(default_factory=list)
    flagged: list[int] = field(default_factory=list)
    moved: list[int] = field(default_factory=list)


def build_plan(inputs: Inputs, previous: list[Ticket] | None, rebuild: bool) -> Outcome:
    rules = inputs.rules
    catalog_ids = {e.frontend_question_id for e in inputs.catalog.entries}
    entries = {e.frontend_question_id: e for e in inputs.catalog.entries}
    keys = {n: group_of(entries[n], inputs) for n in sorted(entries)}
    valid_groups = {s.rule_id for s in rules.specialized}
    valid_groups |= {c.concept_id for c in rules.concepts} | {rules.fallback_id}
    tickets: dict[str, Ticket] = {}
    outcome = Outcome([])

    for number, issue in sorted(rules.individual.items()):
        if number not in entries:
            raise ToolError(
                f"the rules name problem {number}, which is not in the catalog"
            )
        tickets[f"problem-{number}"] = Ticket(
            f"problem-{number}",
            "individual",
            f"problem-{number}",
            None,
            "pending",
            "",
            "",
            issue,
            [number],
            [],
        )

    kept: dict[int, str] = {}
    carried: dict[str, Ticket] = {}
    for old in previous or []:
        if old.kind == "individual":
            continue
        carried[old.ticket_id] = old
        if rebuild:
            continue
        if old.rule not in valid_groups:
            continue
        tickets[old.ticket_id] = Ticket(
            old.ticket_id,
            "class",
            old.rule,
            old.difficulty,
            old.status,
            old.reason,
            old.note,
            old.issue,
            [],
            [],
        )
        for number in old.entries:
            if number in catalog_ids and number not in rules.individual:
                tickets[old.ticket_id].entries.append(number)
                kept[number] = old.ticket_id
            elif number not in catalog_ids:
                tickets[old.ticket_id].removed.append(number)
                outcome.flagged.append(number)
        for number in old.removed:
            if number not in catalog_ids:
                tickets[old.ticket_id].removed.append(number)
            # A removed problem that came back is placed again as a new one.

    unplaced = [
        n for n in sorted(entries) if n not in kept and n not in rules.individual
    ]
    by_prefix: dict[str, list[int]] = {}
    for number in unplaced:
        by_prefix.setdefault(prefix_of(*keys[number]), []).append(number)
    for prefix, numbers in sorted(by_prefix.items()):
        group, difficulty = keys[numbers[0]]
        existing = sorted(
            t.ticket_id
            for t in tickets.values()
            if t.kind == "class" and t.ticket_id.rsplit("-", 1)[0] == prefix
        )
        if not existing:
            count = math.ceil(len(numbers) / rules.ticket_size)
            width = math.ceil(len(numbers) / count)
            for index in range(count):
                ticket = _new_ticket(prefix, index + 1, group, difficulty)
                ticket.entries = numbers[index * width : (index + 1) * width]
                tickets[ticket.ticket_id] = ticket
                outcome.placed.extend(ticket.entries)
            continue
        for number in numbers:
            room = [
                tickets[i]
                for i in existing
                if len(tickets[i].entries) < rules.ticket_size
            ]
            if room:
                room[0].entries.append(number)
            else:
                nxt = 1 + max(int(i.rsplit("-", 1)[1]) for i in existing)
                ticket = _new_ticket(prefix, nxt, group, difficulty)
                ticket.entries.append(number)
                tickets[ticket.ticket_id] = ticket
                existing.append(ticket.ticket_id)
            outcome.placed.append(number)

    for ticket in tickets.values():
        if ticket.kind == "class":
            ticket.entries.sort()
            ticket.removed = sorted(set(ticket.removed))
    if rebuild:
        for ticket_id, ticket in tickets.items():
            earlier = carried.get(ticket_id)
            if earlier is not None and ticket.kind == "class":
                ticket.issue = earlier.issue
                if earlier.status == "in_progress" and ticket.status == "pending":
                    ticket.status = "in_progress"
    _finish(tickets, inputs)
    outcome.tickets = _ordered(tickets, inputs)
    outcome.placed.sort()
    outcome.flagged = sorted(set(outcome.flagged))
    return outcome


def _new_ticket(prefix: str, index: int, group: str, difficulty: str | None) -> Ticket:
    return Ticket(
        f"{prefix}-{index:02d}", "class", group, difficulty, "pending", "", "", None
    )


def _finish(tickets: dict[str, Ticket], inputs: Inputs) -> None:
    """Fill status, reason, note and title from the rules, which own them."""
    rules = inputs.rules
    specialized = {s.rule_id: s for s in rules.specialized}
    concepts = {c.concept_id: c for c in rules.concepts}
    counts: dict[str, int] = {}
    for ticket in tickets.values():
        if ticket.kind == "class":
            prefix = ticket.ticket_id.rsplit("-", 1)[0]
            counts[prefix] = counts.get(prefix, 0) + 1
    entries = {e.frontend_question_id: e for e in inputs.catalog.entries}
    for ticket in tickets.values():
        if ticket.kind == "individual":
            number = ticket.entries[0]
            ticket.title = (
                f"Prepare LeetCode {number}: {entries[number].title} (Python)"
            )
            continue
        prefix = ticket.ticket_id.rsplit("-", 1)[0]
        index = int(ticket.ticket_id.rsplit("-", 1)[1])
        suffix = f" ({index} of {counts[prefix]})" if counts[prefix] > 1 else ""
        if ticket.rule in specialized:
            rule = specialized[ticket.rule]
            ticket.status = "blocked"
            ticket.reason = rule.reason
            ticket.note = ""
            ticket.title = f"Track {rule.title}{suffix}"
        elif ticket.rule in concepts:
            name = inputs.curriculum.names[ticket.rule].lower()
            if ticket.status == "blocked":
                ticket.status = "pending"
            ticket.reason = ""
            ticket.note = concepts[ticket.rule].note
            ticket.title = f"Prepare {name} problems, {ticket.difficulty}{suffix}"
        else:
            if ticket.status == "blocked":
                ticket.status = "pending"
            ticket.reason = ""
            ticket.note = rules.fallback_note
            ticket.title = f"Prepare {rules.fallback_title}{suffix}"


def _ordered(tickets: dict[str, Ticket], inputs: Inputs) -> list[Ticket]:
    rules = inputs.rules
    rank: dict[str, int] = {}
    for number in sorted(rules.individual):
        rank[f"problem-{number}"] = len(rank)
    for rule in rules.specialized:
        rank[rule.rule_id] = len(rank)
    for concept in rules.concepts:
        rank[concept.concept_id] = len(rank)
    rank[rules.fallback_id] = len(rank)

    def sort_key(ticket: Ticket) -> tuple[int, int, int]:
        difficulty = DIFFICULTIES.index(ticket.difficulty) if ticket.difficulty else 0
        index = int(ticket.ticket_id.rsplit("-", 1)[1]) if ticket.kind == "class" else 0
        return rank[ticket.rule], difficulty, index

    return sorted(tickets.values(), key=sort_key)


def render_plan(outcome: Outcome, inputs: Inputs) -> str:
    head = {
        "schema_version": 1,
        "platform": inputs.catalog.platform,
        "ticket_size": inputs.rules.ticket_size,
        "sources": {
            "catalog_fetched_on": inputs.catalog.fetched_on,
            "topics_fetched_on": inputs.topics_fetched_on,
        },
    }
    lines = ["{"]
    for key, value in head.items():
        lines.append(f"  {json.dumps(key)}: {json.dumps(value)},")
    lines.append('  "classes": [')
    blocks = []
    for ticket in outcome.tickets:
        data = ticket.to_dict()
        fields = [
            f"      {json.dumps(key)}: {json.dumps(data[key])}"
            for key in CLASS_KEYS
            if key != "note" or data["note"]
        ]
        blocks.append("    {\n" + ",\n".join(fields) + "\n    }")
    lines.append(",\n".join(blocks))
    lines += ["  ]", "}", ""]
    return "\n".join(lines)


def write_atomically(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    handle, temporary = tempfile.mkstemp(
        dir=path.parent, prefix=".plan-", suffix=".tmp"
    )
    try:
        with os.fdopen(handle, "w", encoding="utf-8", newline="\n") as stream:
            stream.write(text)
        os.replace(temporary, path)
    except BaseException:
        Path(temporary).unlink(missing_ok=True)
        raise


def problems_in_wrong_count(tickets: list[Ticket], catalog_ids: set[int]) -> list[str]:
    """Every problem must sit in exactly one ticket's entries."""
    seen: dict[int, int] = {}
    for ticket in tickets:
        for number in ticket.entries:
            seen[number] = seen.get(number, 0) + 1
    errors = []
    for number in sorted(catalog_ids):
        count = seen.get(number, 0)
        if count == 0:
            errors.append(f"problem {number} is in no ticket")
        elif count > 1:
            errors.append(f"problem {number} is in more than one ticket")
    for number in sorted(set(seen) - catalog_ids):
        errors.append(f"problem {number} is in a ticket but not in the catalog")
    for ticket in tickets:
        for number in ticket.removed:
            if number in catalog_ids:
                errors.append(
                    f"problem {number} is marked removed but is in the catalog"
                )
    return errors


def drift_of(tickets: list[Ticket], inputs: Inputs) -> list[int]:
    entries = {e.frontend_question_id: e for e in inputs.catalog.entries}
    drifted = []
    for ticket in tickets:
        for number in ticket.entries:
            if number in entries:
                group, difficulty = group_of(entries[number], inputs)
                if ticket.kind == "individual":
                    continue
                if (group, difficulty) != (ticket.rule, ticket.difficulty):
                    drifted.append(number)
    return sorted(drifted)


def plan_command(args: argparse.Namespace) -> int:
    inputs = load_inputs(args)
    previous = read_plan(args.plan) if args.plan.exists() and not args.rebuild else None
    if args.rebuild and args.plan.exists():
        previous = read_plan(args.plan)
    outcome = build_plan(inputs, previous, args.rebuild)
    write_atomically(args.plan, render_plan(outcome, inputs))
    count = len(inputs.catalog.entries)
    print(f"planned {count} problems into {len(outcome.tickets)} tickets: {args.plan}")
    if previous is not None and not args.rebuild:
        print(f"placed {len(outcome.placed)} new problem(s) without moving any other")
    if outcome.flagged:
        shown = ", ".join(str(n) for n in outcome.flagged)
        print(f"removed from the catalog and flagged, not dropped: {shown}")
    return 0


def check_command(args: argparse.Namespace) -> int:
    inputs = load_inputs(args)
    if not args.plan.exists():
        raise ToolError(f"there is no plan at {args.plan}; run `plan` first")
    tickets = read_plan(args.plan)
    catalog_ids = {e.frontend_question_id for e in inputs.catalog.entries}
    errors = problems_in_wrong_count(tickets, catalog_ids)
    ids = [t.ticket_id for t in tickets]
    if len(ids) != len(set(ids)):
        errors.append("a ticket id is repeated")
    for ticket in tickets:
        if len(ticket.entries) > inputs.rules.ticket_size:
            errors.append(
                f"ticket {ticket.ticket_id} holds {len(ticket.entries)} problems, "
                f"over the limit of {inputs.rules.ticket_size}"
            )
    for number, issue in inputs.rules.individual.items():
        match = [t for t in tickets if t.ticket_id == f"problem-{number}"]
        if not match or match[0].issue != issue or match[0].entries != [number]:
            errors.append(f"the ticket for problem {number} does not match the rules")
    if not errors:
        outcome = build_plan(inputs, tickets, rebuild=False)
        if render_plan(outcome, inputs) != args.plan.read_text(encoding="utf-8"):
            errors.append(
                "the plan is out of date for the catalog, topics or rules; "
                "run `plan` to update it"
            )
    for line in errors:
        print(line, file=sys.stderr)
    if errors:
        return 1
    count = len(catalog_ids)
    print(f"{count} problems in {len(tickets)} tickets, each mapped exactly once.")
    drifted = drift_of(tickets, inputs)
    if drifted:
        shown = ", ".join(str(n) for n in drifted[:12]) + (
            " ..." if len(drifted) > 12 else ""
        )
        message = (
            f"drift: {len(drifted)} problem(s) sit in a ticket the rules no longer "
            f"pick: {shown}"
        )
        if args.strict:
            print(message, file=sys.stderr)
            return 1
        print(message)
    return 0


def entry_statuses(tickets: list[Ticket], args: argparse.Namespace) -> dict[int, str]:
    statuses: dict[int, str] = {}
    cache: dict[int, bool] = {}
    for ticket in tickets:
        for number in ticket.entries:
            if number not in cache:
                cache[number] = exercise_status(
                    args.problems_dir, args.references, "leetcode", str(number)
                ).ready
            if cache[number]:
                statuses[number] = "ready"
            elif ticket.status == "blocked":
                statuses[number] = "blocked"
            elif ticket.status == "in_progress":
                statuses[number] = "in_progress"
            else:
                statuses[number] = "pending"
    return statuses


def effective_status(ticket: Ticket, statuses: dict[int, str]) -> str:
    """Ready once every problem in the ticket is; otherwise what the plan says."""
    if ticket.entries and all(statuses[n] == "ready" for n in ticket.entries):
        return "ready"
    return ticket.status


def count_of(numbers: list[int], statuses: dict[int, str]) -> dict[str, int]:
    counts = {name: 0 for name in STATUSES}
    for number in numbers:
        counts[statuses[number]] += 1
    return counts


def report_command(args: argparse.Namespace) -> int:
    inputs = load_inputs(args)
    if not args.plan.exists():
        raise ToolError(f"there is no plan at {args.plan}; run `plan` first")
    tickets = read_plan(args.plan)
    catalog_ids = {e.frontend_question_id for e in inputs.catalog.entries}
    once = not problems_in_wrong_count(tickets, catalog_ids)
    statuses = entry_statuses(tickets, args)
    all_numbers = sorted(statuses)
    removed = sorted({n for t in tickets for n in t.removed})
    lists = []
    if args.lists_dir.is_dir():
        try:
            for item in load_lists(args.lists_dir, inputs.catalog):
                numbers = [p.frontend_question_id for p in item.problems]
                lists.append(
                    {
                        "id": item.list_id,
                        "name": item.name,
                        "size": item.size,
                        "counts": count_of(numbers, statuses),
                    }
                )
        except ListError as error:
            raise ToolError(str(error)) from error
    report = {
        "catalog_fetched_on": inputs.catalog.fetched_on,
        "problems": len(all_numbers),
        "exactly_once": once,
        "removed": len(removed),
        "totals": count_of(all_numbers, statuses),
        "classes": [
            {
                "id": t.ticket_id,
                "title": t.title,
                "status": effective_status(t, statuses),
                "issue": t.issue,
                "size": len(t.entries),
                "counts": count_of(t.entries, statuses),
            }
            for t in tickets
        ],
        "lists": lists,
    }
    if args.json:
        print(json.dumps(report, indent=2))
    else:
        print(format_report(report))
    return 0 if once else 1


def format_report(report: dict[str, Any]) -> str:
    totals = report["totals"]
    verdict = (
        "each mapped exactly once"
        if report["exactly_once"]
        else "NOT every problem is mapped exactly once"
    )
    lines = [
        f"Catalog coverage (snapshot {report['catalog_fetched_on']}): "
        f"{report['problems']} problems, {verdict}",
        f"  ready {totals['ready']}, in progress {totals['in_progress']}, "
        f"blocked {totals['blocked']}, pending {totals['pending']}",
    ]
    if report["removed"]:
        lines.append(
            f"  removed from the catalog but kept in their tickets: {report['removed']}"
        )
    lines.append("")
    lines.append(
        f"{'ticket':<26}{'status':<13}{'size':>5}  counts                      issue"
    )
    for item in report["classes"]:
        c = item["counts"]
        issue = f"#{item['issue']}" if item["issue"] else "not created"
        lines.append(
            f"{item['id']:<26}{item['status']:<13}{item['size']:>5}  "
            f"ready {c['ready']} blocked {c['blocked']} pending {c['pending']}"
            f" in-progress {c['in_progress']}  {issue}"
        )
    if report["lists"]:
        lines.append("")
        lines.append("Curated lists")
        for item in report["lists"]:
            c = item["counts"]
            lines.append(
                f"  {item['id']:<22}{item['size']:>4}: ready {c['ready']}, "
                f"in progress {c['in_progress']}, blocked {c['blocked']}, "
                f"pending {c['pending']}"
            )
    return "\n".join(lines)


def render_command(args: argparse.Namespace) -> int:
    inputs = load_inputs(args)
    if not args.plan.exists():
        raise ToolError(f"there is no plan at {args.plan}; run `plan` first")
    tickets = read_plan(args.plan)
    chosen = next((t for t in tickets if t.ticket_id == args.ticket), None)
    if chosen is None:
        known = ", ".join(t.ticket_id for t in tickets)
        raise ToolError(
            f"there is no ticket named {args.ticket!r}. Known tickets: {known}"
        )
    print(render_body(chosen, inputs))
    return 0


def render_body(ticket: Ticket, inputs: Inputs) -> str:
    entries = {e.frontend_question_id: e for e in inputs.catalog.entries}
    lines = [
        f"# {ticket.title}",
        "",
        "Sub-issue of #1. Part of #15, which maps every catalog problem to one "
        "preparation ticket.",
        "",
    ]
    if ticket.kind == "individual":
        lines += ["## Problem", ""]
    elif ticket.status == "blocked":
        lines += [
            "## Outcome",
            "",
            "Keep these problems visible and counted until what blocks them is "
            "resolved. Nothing here is claimed ready.",
            "",
            "## Blocked",
            "",
            ticket.reason,
            "",
            "These problems stay blocked until that is resolved. A blocked problem "
            "is never counted as ready.",
            "",
            "## Problems",
            "",
        ]
    else:
        lines += [
            "## Outcome",
            "",
            "Each problem below ends up either ready for local practice, with the "
            "evidence described under Readiness, or recorded as out of scope or "
            "blocked with a documented reason.",
            "",
        ]
        if ticket.note:
            lines += [ticket.note, ""]
        lines += ["## Problems", ""]
    for number in ticket.entries:
        e = entries[number]
        lines.append(f"- [ ] {number} {e.title} ({e.difficulty}, {e.slug})")
    if (
        ticket.status != "blocked"
        and ticket.kind == "class"
        and ticket.rule in inputs.curriculum.names
    ):
        lines += ["", "## Prerequisites", ""]
        lines += prerequisite_lines(ticket.rule, inputs.curriculum)
    lines += ["", "## Readiness", "", READINESS_BAR, ""]
    lines += [
        "## Delivery rule",
        "",
        "Implement and verify as one coherent outcome. Before closing completed "
        "work, post a plain-English summary with verification, PR links and "
        "relevant references; state whether merge is pending. Never mark "
        "unfinished work complete.",
    ]
    return "\n".join(lines)


def prerequisite_lines(concept: str, curriculum: Curriculum) -> list[str]:
    needed: set[str] = set()
    stack = list(curriculum.prerequisites[concept])
    while stack:
        item = stack.pop()
        if item not in needed:
            needed.add(item)
            stack.extend(curriculum.prerequisites[item])
    ordered = [c for c in curriculum.order if c in needed]
    if not ordered:
        return ["None; this is the first concept."]
    return [f"- {curriculum.names[c]} (`{c}`)" for c in ordered]


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Plan catalog preparation tickets.")
    parser.add_argument("--catalog", type=Path, default=DEFAULT_CATALOG)
    parser.add_argument("--topics", type=Path, default=DEFAULT_TOPICS)
    parser.add_argument("--rules", type=Path, default=DEFAULT_RULES)
    parser.add_argument("--curriculum", type=Path, default=DEFAULT_CURRICULUM)
    parser.add_argument("--plan", type=Path, default=DEFAULT_PLAN)
    parser.add_argument("--lists-dir", type=Path, default=DEFAULT_LISTS)
    parser.add_argument("--problems-dir", type=Path, default=DEFAULT_PROBLEMS)
    parser.add_argument("--references", type=Path, default=REFERENCES_DIR)
    commands = parser.add_subparsers(dest="command", required=True)
    plan = commands.add_parser("plan", help="write or update the plan")
    plan.add_argument(
        "--rebuild",
        action="store_true",
        help="apply the rules afresh, keeping issue numbers and progress",
    )
    check = commands.add_parser("check", help="verify the plan is complete and current")
    check.add_argument("--strict", action="store_true", help="fail on drift too")
    report = commands.add_parser("report", help="coverage by status, ticket and list")
    report.add_argument("--json", action="store_true")
    render = commands.add_parser("render", help="print one ticket's body")
    render.add_argument("ticket")
    return parser


def main(argv: list[str]) -> int:
    args = build_parser().parse_args(argv)
    handlers = {
        "plan": plan_command,
        "check": check_command,
        "report": report_command,
        "render": render_command,
    }
    try:
        return handlers[args.command](args)
    except ToolError as error:
        print(f"tools/plan_catalog.py: error: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
