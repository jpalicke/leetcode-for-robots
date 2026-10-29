# ABOUTME: Loads a deterministic concept map and validates starter catalog placements.
# ABOUTME: Projects eligible objectives without revealing internal technique metadata.

import json
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from practice.catalog import Catalog, Entry

DEFAULT_CURRICULUM_PATH = (
    Path(__file__).resolve().parents[2] / "curriculum" / "core.json"
)


class CurriculumError(Exception):
    """The curriculum or mastered concept selection is invalid."""


@dataclass(frozen=True)
class Concept:
    id: str
    name: str
    prerequisites: tuple[str, ...]


@dataclass(frozen=True)
class Placement:
    problem: Entry
    concept: str
    prerequisites: tuple[str, ...]


@dataclass(frozen=True)
class Objective:
    label: str
    problems: tuple[Entry, ...]

    def to_dict(self) -> dict[str, object]:
        return {
            "label": self.label,
            "problems": [
                {
                    "platform": p.platform,
                    "problem_id": p.frontend_question_id,
                    "title": p.title,
                }
                for p in self.problems
            ],
        }


@dataclass(frozen=True)
class Curriculum:
    concepts: tuple[Concept, ...]
    starters: tuple[int, ...]
    placements: tuple[Placement, ...]

    def label_for(self, concept_id: str) -> str:
        """The learner-safe name of a concept's objective, such as "Objective 3"."""
        for index, concept in enumerate(self.concepts, 1):
            if concept.id == concept_id:
                return f"Objective {index}"
        raise CurriculumError("unknown concept")

    def next_objectives(self, mastered: Iterable[str] = ()) -> tuple[Objective, ...]:
        known = {c.id for c in self.concepts}
        completed = set(mastered)
        if not completed <= known:
            raise CurriculumError("unknown mastered concept")
        return tuple(
            Objective(
                self.label_for(concept.id),
                tuple(
                    p.problem
                    for p in self.placements
                    if p.concept == concept.id
                    and all(required in completed for required in p.prerequisites)
                ),
            )
            for concept in self.concepts
            if concept.id not in completed
            and all(required in completed for required in concept.prerequisites)
        )


def load_curriculum(path: Path, catalog: Catalog) -> Curriculum:
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
        raise CurriculumError(f"cannot read curriculum {path}: {error}") from error
    return parse_curriculum(raw, catalog)


def _record(raw: object, where: str) -> dict[str, Any]:
    if not isinstance(raw, dict):
        raise CurriculumError(f"{where} must be an object")
    return raw


def _list(raw: dict[str, Any], field: str) -> list[Any]:
    value = raw.get(field)
    if not isinstance(value, list):
        raise CurriculumError(f"{field} must be a list")
    return value


def _text(raw: dict[str, Any], field: str) -> str:
    value = raw.get(field)
    if not isinstance(value, str) or not value.strip():
        raise CurriculumError(f"{field} must be a non-empty string")
    return value


def _references(raw: dict[str, Any], field: str) -> tuple[str, ...]:
    values = _list(raw, field)
    if any(not isinstance(value, str) or not value for value in values):
        raise CurriculumError(f"{field} must contain concept ids")
    if len(values) != len(set(values)):
        raise CurriculumError(f"duplicate {field}")
    return tuple(values)


def _problem_id(raw: object) -> int:
    if isinstance(raw, bool) or not isinstance(raw, int) or raw < 1:
        raise CurriculumError("problem id must be a positive integer")
    return raw


def parse_curriculum(raw: object, catalog: Catalog) -> Curriculum:
    data = _record(raw, "curriculum")
    if _text(data, "platform") != catalog.platform:
        raise CurriculumError("curriculum platform does not match catalog platform")
    if type(data.get("version")) is not int or data["version"] != 1:
        raise CurriculumError("curriculum version must be 1")
    concepts = tuple(
        Concept(
            _text(record, "id"),
            _text(record, "name"),
            _references(record, "prerequisites"),
        )
        for item in _list(data, "concepts")
        for record in (_record(item, "concept"),)
    )
    ids = tuple(c.id for c in concepts)
    if not ids or len(set(ids)) != len(ids):
        raise CurriculumError("concept ids must be non-empty and unique")
    by_id = {c.id: c for c in concepts}
    for concept in concepts:
        if any(p not in by_id for p in concept.prerequisites):
            raise CurriculumError("unknown concept prerequisite")
    # Iterative traversal avoids recursion limits on custom maps.
    remaining = set(ids)
    visited: set[str] = set()
    while remaining:
        ready = [
            c.id
            for c in concepts
            if c.id in remaining and all(p in visited for p in c.prerequisites)
        ]
        if not ready:
            raise CurriculumError("concept prerequisite cycle")
        visited.update(ready)
        remaining.difference_update(ready)
    positions = {concept_id: index for index, concept_id in enumerate(ids)}
    for concept in concepts:
        if any(positions[p] >= positions[concept.id] for p in concept.prerequisites):
            raise CurriculumError("concept order must place prerequisites first")
    starters = tuple(_problem_id(item) for item in _list(data, "starters"))
    if not starters or len(set(starters)) != len(starters):
        raise CurriculumError("starter ids must be non-empty and unique")
    entries = {e.frontend_question_id: e for e in catalog.entries}
    if any(p not in entries for p in starters):
        raise CurriculumError("unknown catalog problem")
    placements: list[Placement] = []
    assigned: set[int] = set()
    for item in _list(data, "placements"):
        record = _record(item, "placement")
        problem_id = _problem_id(record.get("problem_id"))
        if problem_id not in starters or problem_id in assigned:
            raise CurriculumError("extra or duplicate starter assignment")
        concept_id = _text(record, "concept")
        prerequisites = _references(record, "prerequisites")
        if concept_id not in by_id or any(p not in by_id for p in prerequisites):
            raise CurriculumError("unknown placement concept")
        if any(positions[p] >= positions[concept_id] for p in prerequisites):
            raise CurriculumError("placement prerequisites must precede its concept")
        if not set(by_id[concept_id].prerequisites) <= set(prerequisites):
            raise CurriculumError("placement must include its concept prerequisites")
        placements.append(Placement(entries[problem_id], concept_id, prerequisites))
        assigned.add(problem_id)
    if assigned != set(starters):
        raise CurriculumError("unplaced starter problem")
    # Starter selection is the canonical problem order, independent of placement order.
    by_problem = {p.problem.frontend_question_id: p for p in placements}
    return Curriculum(concepts, starters, tuple(by_problem[p] for p in starters))
