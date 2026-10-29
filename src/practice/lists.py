# ABOUTME: Loads curated problem lists (LeetCode 150, Blind 75) and checks them.
# ABOUTME: A list is an overlay on the catalog: ordered, grouped, never a ticket.

import json
import re
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path
from typing import Any

from practice.catalog import Catalog
from practice.exercises import Exercise, exercise_status

DEFAULT_LISTS_DIR = Path(__file__).resolve().parents[2] / "catalog" / "lists"
SCHEMA_VERSION = 1
LIST_ID = re.compile(r"[a-z0-9]+(-[a-z0-9]+)*")
TOP_LEVEL_KEYS = {
    "schema_version",
    "id",
    "name",
    "platform",
    "size",
    "source",
    "groups",
}
SOURCE_KEYS = {
    "kind",
    "url",
    "retrieved_on",
    "repository",
    "revision",
    "path",
    "license",
    "plan_slug",
    "flag",
    "note",
}
GROUP_KEYS = {"name", "problems"}
PROBLEM_KEYS = {"id", "slug"}


class ListError(Exception):
    """A list file cannot be read or fails validation."""


@dataclass(frozen=True)
class ListProblem:
    frontend_question_id: int
    slug: str
    title: str
    difficulty: str
    paid_only: bool


@dataclass(frozen=True)
class ListGroup:
    name: str
    problems: tuple[ListProblem, ...]


@dataclass(frozen=True)
class ProblemList:
    list_id: str
    name: str
    platform: str
    size: int
    source: dict[str, str]
    groups: tuple[ListGroup, ...]
    problems: tuple[ListProblem, ...] = field(init=False)

    def __post_init__(self) -> None:
        flat = tuple(p for group in self.groups for p in group.problems)
        object.__setattr__(self, "problems", flat)


@dataclass(frozen=True)
class ProblemStatus:
    problem: ListProblem
    status: str  # "ready", "blocked" or "pending".
    reason: str  # Empty when ready.


def load_lists(directory: Path, catalog: Catalog) -> tuple[ProblemList, ...]:
    if not directory.is_dir():
        raise ListError(f"{directory} is not a directory")
    paths = sorted(directory.glob("*.json"))
    return tuple(load_list(path, catalog) for path in paths)


def load_list(path: Path, catalog: Catalog) -> ProblemList:
    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as error:
        raise ListError(f"cannot read list file {path}: {error}") from error
    try:
        data = json.loads(text)
    except json.JSONDecodeError as error:
        raise ListError(
            f"list file {path.name} is not valid JSON (line {error.lineno}, "
            f"column {error.colno}): {error.msg}. The file may be truncated."
        ) from error
    try:
        result = parse_list(data, catalog)
        if path.name != f"{result.list_id}.json":
            raise ListError(f"file name must be {result.list_id}.json")
    except ListError as error:
        raise ListError(f"list file {path.name} is invalid: {error}") from error
    return result


def parse_list(data: object, catalog: Catalog) -> ProblemList:
    if not isinstance(data, dict):
        raise ListError("the top level must be a JSON object")
    _no_unknown(data, TOP_LEVEL_KEYS, "the list")
    if data.get("schema_version") != SCHEMA_VERSION:
        raise ListError(f"schema_version must be {SCHEMA_VERSION}")
    list_id = data.get("id")
    if not isinstance(list_id, str) or not LIST_ID.fullmatch(list_id):
        raise ListError("id must be lowercase letters, digits and single hyphens")
    name = _text(data, "name", "the list")
    platform = _text(data, "platform", "the list")
    if platform != catalog.platform:
        raise ListError(
            f"platform {platform!r} does not match the catalog's {catalog.platform!r}"
        )
    size = data.get("size")
    if isinstance(size, bool) or not isinstance(size, int) or size < 1:
        raise ListError("size must be a positive whole number")
    source = _parse_source(data.get("source"))
    groups = _parse_groups(data.get("groups"), catalog)
    count = sum(len(group.problems) for group in groups)
    if count != size:
        raise ListError(f"declares {size} problems but has {count}")
    seen: set[int] = set()
    for group in groups:
        for problem in group.problems:
            if problem.frontend_question_id in seen:
                raise ListError(
                    f"problem {problem.frontend_question_id} appears more than once"
                )
            seen.add(problem.frontend_question_id)
    return ProblemList(list_id, name, platform, size, source, groups)


def _parse_source(raw: object) -> dict[str, str]:
    if not isinstance(raw, dict):
        raise ListError("source must be an object")
    _no_unknown(raw, SOURCE_KEYS, "source")
    kind = _text(raw, "kind", "source")
    url = _text(raw, "url", "source")
    if not url.startswith("https://"):
        raise ListError("source url must be an https address")
    retrieved = _text(raw, "retrieved_on", "source")
    try:
        date.fromisoformat(retrieved)
    except ValueError as error:
        raise ListError(
            f"source retrieved_on must be an ISO date such as 2026-10-29, "
            f"got {retrieved!r}"
        ) from error
    source = {"kind": kind, "url": url, "retrieved_on": retrieved}
    for key in sorted(SOURCE_KEYS - set(source)):
        if key in raw:
            source[key] = _text(raw, key, "source")
    return source


def _parse_groups(raw: object, catalog: Catalog) -> tuple[ListGroup, ...]:
    if not isinstance(raw, list) or not raw:
        raise ListError("groups must be a non-empty list")
    by_id = {entry.frontend_question_id: entry for entry in catalog.entries}
    groups = []
    for index, group in enumerate(raw):
        where = f"group {index}"
        if not isinstance(group, dict):
            raise ListError(f"{where} must be an object")
        _no_unknown(group, GROUP_KEYS, where)
        group_name = _text(group, "name", where)
        members = group.get("problems")
        if not isinstance(members, list) or not members:
            raise ListError(f"{where} ({group_name}) needs a non-empty problems list")
        problems = []
        for position, member in enumerate(members):
            problems.append(
                _parse_problem(member, f"{where} problem {position}", by_id)
            )
        groups.append(ListGroup(group_name, tuple(problems)))
    return tuple(groups)


def _parse_problem(raw: object, where: str, by_id: dict[int, Any]) -> ListProblem:
    if not isinstance(raw, dict):
        raise ListError(f"{where} must be an object")
    _no_unknown(raw, PROBLEM_KEYS, where)
    number = raw.get("id")
    if isinstance(number, bool) or not isinstance(number, int) or number < 1:
        raise ListError(f"{where}: id must be a positive whole number")
    slug = _text(raw, "slug", where)
    entry = by_id.get(number)
    if entry is None:
        raise ListError(f"problem {number} is not in the catalog")
    if entry.slug != slug:
        raise ListError(
            f"problem {number} has slug {slug!r} but the catalog says {entry.slug!r}"
        )
    return ListProblem(number, slug, entry.title, entry.difficulty, entry.paid_only)


def _text(source: dict[str, Any], key: str, where: str) -> str:
    value = source.get(key)
    if not isinstance(value, str) or not value:
        raise ListError(f"{where}: {key} must be a non-empty string")
    return value


def _no_unknown(source: dict[str, Any], allowed: set[str], where: str) -> None:
    unknown = sorted(set(source) - allowed)
    if unknown:
        raise ListError(f"{where} has unknown keys: {', '.join(unknown)}")


def list_statuses(
    problem_list: ProblemList,
    problems_dir: Path,
    references: Path,
    cache: dict[int, Exercise] | None = None,
) -> tuple[ProblemStatus, ...]:
    """Ready, blocked or pending for each problem, in list order.

    Ready means the exercise package passes `practice readiness`. A premium
    problem without one is blocked. Everything else is pending, and never
    shown as runnable. Pass one cache to several lists to check a problem once.
    """
    checked = cache if cache is not None else {}
    statuses = []
    for problem in problem_list.problems:
        number = problem.frontend_question_id
        if number not in checked:
            checked[number] = exercise_status(
                problems_dir, references, problem_list.platform, str(number)
            )
        exercise = checked[number]
        if exercise.ready:
            statuses.append(ProblemStatus(problem, "ready", ""))
        elif problem.paid_only:
            statuses.append(
                ProblemStatus(problem, "blocked", "Blocked: premium problem.")
            )
        else:
            statuses.append(ProblemStatus(problem, "pending", exercise.reason))
    return tuple(statuses)


def count_statuses(statuses: tuple[ProblemStatus, ...]) -> dict[str, int]:
    counts = {"ready": 0, "blocked": 0, "pending": 0}
    for item in statuses:
        counts[item.status] += 1
    return counts
