# ABOUTME: Exercises curriculum validation with real catalog records and malformed data.
# ABOUTME: Checks deterministic prerequisites and neutral learner objective projection.

import json
from pathlib import Path
from typing import Any, cast

import pytest

from practice.catalog import DEFAULT_CATALOG_PATH, load_catalog
from practice.curriculum import (
    DEFAULT_CURRICULUM_PATH,
    CurriculumError,
    load_curriculum,
    parse_curriculum,
)


def data() -> dict[str, Any]:
    return cast(
        dict[str, Any], json.loads(DEFAULT_CURRICULUM_PATH.read_text(encoding="utf-8"))
    )


def test_committed_map_and_frontier() -> None:
    curriculum = load_curriculum(
        DEFAULT_CURRICULUM_PATH, load_catalog(DEFAULT_CATALOG_PATH)
    )
    assert [c.id for c in curriculum.concepts] == [
        "arrays",
        "strings",
        "lookup",
        "sequences",
        "linked",
        "trees",
        "graphs",
        "dp",
    ]
    assert curriculum.starters == (1, 217, 242, 20, 704, 121)
    assert [
        (p.problem.frontend_question_id, p.concept, p.prerequisites)
        for p in curriculum.placements
    ] == [
        (1, "arrays", ()),
        (217, "lookup", ("arrays",)),
        (242, "strings", ("arrays",)),
        (20, "sequences", ("arrays", "strings", "lookup")),
        (704, "sequences", ("arrays", "strings", "lookup")),
        (121, "sequences", ("arrays", "strings", "lookup")),
    ]
    assert [o.label for o in curriculum.next_objectives()] == ["Objective 1"]
    assert [o.label for o in curriculum.next_objectives(("arrays",))] == [
        "Objective 2",
        "Objective 3",
    ]
    assert curriculum.next_objectives(tuple(c.id for c in curriculum.concepts)) == ()
    with pytest.raises(CurriculumError, match="mastered"):
        curriculum.next_objectives(("absent",))


@pytest.mark.parametrize(
    "variant",
    [
        "unknown",
        "cycle",
        "duplicate",
        "missing",
        "extra",
        "problem",
        "assignment",
        "prerequisite",
        "starter",
        "shape",
    ],
)
def test_invalid_maps(variant: str) -> None:
    raw = data()
    if variant == "unknown":
        raw["concepts"][0]["prerequisites"] = ["absent"]
    elif variant == "cycle":
        raw["concepts"][0]["prerequisites"] = ["dp"]
    elif variant == "duplicate":
        raw["concepts"].append(raw["concepts"][0])
    elif variant == "missing":
        raw["placements"].pop()
    elif variant == "extra":
        raw["placements"].append(
            {"problem_id": 2, "concept": "arrays", "prerequisites": []}
        )
    elif variant == "problem":
        raw["starters"][0] = 99999999
        raw["placements"][0]["problem_id"] = 99999999
    elif variant == "assignment":
        raw["placements"].append(raw["placements"][0])
    elif variant == "prerequisite":
        raw["placements"][0]["prerequisites"] = ["absent"]
    elif variant == "starter":
        raw["starters"].append(raw["starters"][0])
    else:
        raw["concepts"] = True
    with pytest.raises(CurriculumError):
        parse_curriculum(raw, load_catalog(DEFAULT_CATALOG_PATH))


def test_unreadable_and_invalid_json(tmp_path: Path) -> None:
    path = tmp_path / "curriculum.json"
    catalog = load_catalog(DEFAULT_CATALOG_PATH)
    with pytest.raises(CurriculumError):
        load_curriculum(path, catalog)
    path.write_text("{", encoding="utf-8")
    with pytest.raises(CurriculumError):
        load_curriculum(path, catalog)


@pytest.mark.parametrize(
    "field,value",
    [
        ("version", True),
        ("version", 2),
        ("concepts", []),
        ("starters", []),
        ("starters", [True]),
        ("starters", ["1"]),
        ("placements", [False]),
    ],
)
def test_invalid_field_shapes(field: str, value: object) -> None:
    raw = data()
    raw[field] = value
    with pytest.raises(CurriculumError):
        parse_curriculum(raw, load_catalog(DEFAULT_CATALOG_PATH))


@pytest.mark.parametrize(
    "variant",
    [
        "self",
        "forward",
        "duplicate",
        "nontext",
        "missing",
        "placement-self",
        "placement-missing",
    ],
)
def test_reference_constraints(variant: str) -> None:
    raw = data()
    if variant == "self":
        raw["concepts"][0]["prerequisites"] = ["arrays"]
    elif variant == "forward":
        raw["concepts"][1]["prerequisites"] = ["lookup"]
    elif variant == "duplicate":
        raw["concepts"][1]["prerequisites"] = ["arrays", "arrays"]
    elif variant == "nontext":
        raw["concepts"][0]["prerequisites"] = [{}]
    elif variant == "missing":
        del raw["concepts"][0]["prerequisites"]
    elif variant == "placement-self":
        raw["placements"][0]["prerequisites"] = ["arrays"]
    else:
        raw["placements"][1]["prerequisites"] = []
    with pytest.raises(CurriculumError):
        parse_curriculum(raw, load_catalog(DEFAULT_CATALOG_PATH))


def test_expansion_and_canonical_problem_order() -> None:
    raw = data()
    raw["starters"].append(2)
    raw["placements"].append(
        {"problem_id": 2, "concept": "arrays", "prerequisites": []}
    )
    raw["placements"].reverse()
    curriculum = parse_curriculum(raw, load_catalog(DEFAULT_CATALOG_PATH))
    assert [
        p.frontend_question_id for p in curriculum.next_objectives()[0].problems
    ] == [1, 2]
    frontier = curriculum.next_objectives(("arrays", "strings", "lookup"))
    assert [o.label for o in frontier] == ["Objective 4"]
    assert [p.frontend_question_id for p in frontier[0].problems] == [20, 704, 121]
