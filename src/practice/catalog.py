# ABOUTME: Loads and validates the dated catalog snapshot of a practice platform.
# ABOUTME: Rejects corrupt files with a CatalogError instead of searching them.

import json
from collections.abc import Callable
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any

DEFAULT_CATALOG_PATH = Path(__file__).resolve().parents[2] / "catalog" / "leetcode.json"
DIFFICULTIES = ("easy", "medium", "hard")


class CatalogError(Exception):
    """The catalog file cannot be read or fails validation."""


@dataclass(frozen=True)
class Entry:
    platform: str
    frontend_question_id: int  # The ID learners see; unique within a platform.
    question_id: int  # The platform's internal ID; may differ from the above.
    title: str
    slug: str
    difficulty: str
    paid_only: bool

    @property
    def identity(self) -> tuple[str, int]:
        return (self.platform, self.frontend_question_id)


@dataclass(frozen=True)
class Catalog:
    platform: str
    source_url: str
    fetched_on: str
    entries: tuple[Entry, ...]


def load_catalog(path: Path) -> Catalog:
    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as error:
        raise CatalogError(f"cannot read catalog {path}: {error}") from error
    try:
        data = json.loads(text)
    except json.JSONDecodeError as error:
        raise CatalogError(
            f"catalog {path} is not valid JSON (line {error.lineno}, "
            f"column {error.colno}): {error.msg}. The file may be truncated."
        ) from error
    try:
        return parse_catalog(data)
    except CatalogError as error:
        raise CatalogError(f"catalog {path} is invalid: {error}") from error


def parse_catalog(data: object) -> Catalog:
    if not isinstance(data, dict):
        raise CatalogError("the top level must be a JSON object")
    platform = _text(data, "platform", "catalog")
    source_url = _text(data, "source_url", "catalog")
    fetched_on = _text(data, "fetched_on", "catalog")
    try:
        date.fromisoformat(fetched_on)
    except ValueError as error:
        raise CatalogError(
            f"fetched_on must be an ISO date such as 2026-10-28, got {fetched_on!r}"
        ) from error
    raw_entries = data.get("entries")
    if not isinstance(raw_entries, list) or not raw_entries:
        raise CatalogError("entries must be a non-empty list")

    entries = tuple(
        _parse_entry(raw, f"entry {index}", platform)
        for index, raw in enumerate(raw_entries)
    )
    _require_unique(entries, "frontend_question_id", lambda e: e.frontend_question_id)
    _require_unique(entries, "slug", lambda e: e.slug)
    return Catalog(platform, source_url, fetched_on, entries)


def _parse_entry(raw: object, where: str, platform: str) -> Entry:
    if not isinstance(raw, dict):
        raise CatalogError(f"{where} must be a JSON object")
    entry_platform = _text(raw, "platform", where)
    if entry_platform != platform:
        raise CatalogError(
            f"{where} has platform {entry_platform!r}, expected {platform!r}"
        )
    difficulty = _text(raw, "difficulty", where)
    if difficulty not in DIFFICULTIES:
        raise CatalogError(
            f"{where} has difficulty {difficulty!r}, expected one of {DIFFICULTIES}"
        )
    return Entry(
        platform=entry_platform,
        frontend_question_id=_positive_int(raw, "frontend_question_id", where),
        question_id=_positive_int(raw, "question_id", where),
        title=_text(raw, "title", where),
        slug=_text(raw, "slug", where),
        difficulty=difficulty,
        paid_only=_flag(raw, "paid_only", where),
    )


def _text(source: dict[str, Any], field: str, where: str) -> str:
    value = source.get(field)
    if not isinstance(value, str) or not value:
        raise CatalogError(f"{where}: {field} must be a non-empty string")
    return value


def _positive_int(source: dict[str, Any], field: str, where: str) -> int:
    value = source.get(field)
    # bool is a subclass of int, so it is excluded explicitly.
    if not isinstance(value, int) or isinstance(value, bool) or value < 1:
        raise CatalogError(f"{where}: {field} must be a positive integer")
    return value


def _flag(source: dict[str, Any], field: str, where: str) -> bool:
    value = source.get(field)
    if not isinstance(value, bool):
        raise CatalogError(f"{where}: {field} must be true or false")
    return value


def _require_unique(
    entries: tuple[Entry, ...], field: str, key: Callable[[Entry], object]
) -> None:
    seen: set[object] = set()
    for entry in entries:
        value = key(entry)
        if value in seen:
            raise CatalogError(f"duplicate {field} {value!r}")
        seen.add(value)
