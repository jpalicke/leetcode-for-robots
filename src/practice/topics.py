# ABOUTME: Loads the dated category and topic tags LeetCode gives each catalog problem.
# ABOUTME: Facts only, no problem text; they must cover the catalog exactly.

import json
import re
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any

from practice.catalog import Catalog

DEFAULT_TOPICS_PATH = (
    Path(__file__).resolve().parents[2] / "catalog" / "leetcode-topics.json"
)
SCHEMA_VERSION = 1
CATEGORIES = ("algorithms", "concurrency", "database", "javascript", "pandas", "shell")
TOP_LEVEL_KEYS = {
    "schema_version",
    "platform",
    "source_url",
    "fetched_on",
    "note",
    "entries",
}
ENTRY_KEYS = {"id", "categories", "topics"}
TOPIC = re.compile(r"[a-z0-9]+(-[a-z0-9]+)*")


class TopicsError(Exception):
    """The topics file cannot be read or fails validation."""


@dataclass(frozen=True)
class TopicFacts:
    categories: tuple[str, ...]
    topics: tuple[str, ...]


@dataclass(frozen=True)
class Topics:
    platform: str
    source_url: str
    fetched_on: str
    facts: dict[int, TopicFacts]


def load_topics(path: Path, catalog: Catalog) -> Topics:
    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as error:
        raise TopicsError(f"cannot read topics file {path}: {error}") from error
    try:
        data = json.loads(text)
    except json.JSONDecodeError as error:
        raise TopicsError(
            f"topics file {path.name} is not valid JSON (line {error.lineno}, "
            f"column {error.colno}): {error.msg}. The file may be truncated."
        ) from error
    try:
        return parse_topics(data, catalog)
    except TopicsError as error:
        raise TopicsError(f"topics file {path.name} is invalid: {error}") from error


def parse_topics(data: object, catalog: Catalog) -> Topics:
    if not isinstance(data, dict):
        raise TopicsError("the top level must be a JSON object")
    unknown = sorted(set(data) - TOP_LEVEL_KEYS)
    if unknown:
        raise TopicsError(f"the file has unknown keys: {', '.join(unknown)}")
    if data.get("schema_version") != SCHEMA_VERSION:
        raise TopicsError(f"schema_version must be {SCHEMA_VERSION}")
    platform = _text(data, "platform", "the file")
    if platform != catalog.platform:
        raise TopicsError(
            f"platform {platform!r} does not match the catalog's {catalog.platform!r}"
        )
    source_url = _text(data, "source_url", "the file")
    if not source_url.startswith("https://"):
        raise TopicsError("source_url must be an https address")
    fetched_on = _text(data, "fetched_on", "the file")
    try:
        date.fromisoformat(fetched_on)
    except ValueError as error:
        raise TopicsError(
            f"fetched_on must be an ISO date such as 2026-10-29, got {fetched_on!r}"
        ) from error
    raw = data.get("entries")
    if not isinstance(raw, list) or not raw:
        raise TopicsError("entries must be a non-empty list")
    known = {entry.frontend_question_id for entry in catalog.entries}
    facts: dict[int, TopicFacts] = {}
    for index, item in enumerate(raw):
        number, fact = _parse_entry(item, f"entry {index}")
        if number in facts:
            raise TopicsError(f"problem {number} appears more than once")
        if number not in known:
            raise TopicsError(f"problem {number} is not in the catalog")
        facts[number] = fact
    for number in sorted(known - set(facts)):
        raise TopicsError(f"there are no facts for problem {number}")
    return Topics(platform, source_url, fetched_on, facts)


def _parse_entry(item: object, where: str) -> tuple[int, TopicFacts]:
    if not isinstance(item, dict):
        raise TopicsError(f"{where} must be an object")
    unknown = sorted(set(item) - ENTRY_KEYS)
    if unknown:
        raise TopicsError(f"{where} has unknown keys: {', '.join(unknown)}")
    number = item.get("id")
    if isinstance(number, bool) or not isinstance(number, int) or number < 1:
        raise TopicsError(f"{where}: id must be a positive whole number")
    categories = _slugs(item.get("categories"), f"{where}: categories", minimum=1)
    for category in categories:
        if category not in CATEGORIES:
            raise TopicsError(f"{where}: unknown category {category!r}")
    topics = _slugs(item.get("topics"), f"{where}: topics", minimum=0)
    for topic in topics:
        if not TOPIC.fullmatch(topic):
            raise TopicsError(f"{where}: topic {topic!r} is not a lowercase slug")
    return number, TopicFacts(categories, topics)


def _slugs(value: Any, where: str, *, minimum: int) -> tuple[str, ...]:
    if not isinstance(value, list) or len(value) < minimum:
        raise TopicsError(f"{where} must be a list of at least {minimum} text values")
    if not all(isinstance(item, str) for item in value):
        raise TopicsError(f"{where} must hold text values only")
    if value != sorted(set(value)):
        raise TopicsError(f"{where} must be sorted with no repeats")
    return tuple(value)


def _text(source: dict[str, Any], key: str, where: str) -> str:
    value = source.get(key)
    if not isinstance(value, str) or not value:
        raise TopicsError(f"{where}: {key} must be a non-empty string")
    return value
