# ABOUTME: Integrates curriculum files with catalog titles and neutral public records.
# ABOUTME: Ensures custom content cannot inject technique labels into learner output.

import json
from pathlib import Path

import pytest

from practice.catalog import DEFAULT_CATALOG_PATH, load_catalog
from practice.curriculum import (
    DEFAULT_CURRICULUM_PATH,
    CurriculumError,
    load_curriculum,
)


def test_custom_file_projection(tmp_path: Path) -> None:
    raw = json.loads(DEFAULT_CURRICULUM_PATH.read_text(encoding="utf-8"))
    raw["concepts"][0]["name"] = "SECRET TECHNIQUE"
    raw["placements"][0]["label"] = "SECRET TECHNIQUE"
    path = tmp_path / "map.json"
    path.write_text(json.dumps(raw), encoding="utf-8")
    curriculum = load_curriculum(path, load_catalog(DEFAULT_CATALOG_PATH))
    output = [o.to_dict() for o in curriculum.next_objectives()]
    assert output == [
        {
            "label": "Objective 1",
            "problems": [{"platform": "leetcode", "problem_id": 1, "title": "Two Sum"}],
        }
    ]
    all_output = [o.to_dict() for o in curriculum.next_objectives(("arrays",))]
    assert all_output[1]["problems"] == [
        {"platform": "leetcode", "problem_id": 217, "title": "Contains Duplicate"}
    ]
    assert "SECRET" not in json.dumps(all_output)


def test_catalog_platform_mismatch(tmp_path: Path) -> None:
    raw = json.loads(DEFAULT_CATALOG_PATH.read_text(encoding="utf-8"))
    raw["platform"] = "other"
    for entry in raw["entries"]:
        entry["platform"] = "other"
    path = tmp_path / "catalog.json"
    path.write_text(json.dumps(raw), encoding="utf-8")
    with pytest.raises(CurriculumError, match="platform"):
        load_curriculum(DEFAULT_CURRICULUM_PATH, load_catalog(path))
