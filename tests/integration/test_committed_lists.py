# ABOUTME: Checks that the committed list registry and list files agree.
# ABOUTME: Offline, against the real catalog; the live check is tools/fetch_lists.py.

import json
from pathlib import Path
from typing import Any

import pytest

from practice.catalog import DEFAULT_CATALOG_PATH, load_catalog
from practice.lists import DEFAULT_LISTS_DIR, ProblemList, load_lists
from practice.paths import REPO_ROOT

REGISTRY = REPO_ROOT / "catalog" / "list-sources.json"
FORBIDDEN_KEYS = {"content", "statement", "description", "text", "examples", "code"}


def registry() -> dict[str, Any]:
    loaded = json.loads(REGISTRY.read_text(encoding="utf-8"))
    assert isinstance(loaded, dict)
    return loaded


@pytest.fixture(scope="module")
def lists() -> dict[str, ProblemList]:
    catalog = load_catalog(DEFAULT_CATALOG_PATH)
    return {p.list_id: p for p in load_lists(DEFAULT_LISTS_DIR, catalog)}


def test_every_registered_list_has_a_file_and_every_file_is_registered(
    lists: dict[str, ProblemList],
) -> None:
    assert {item["id"] for item in registry()["lists"]} == set(lists)


def test_each_registered_size_and_name_match_the_file(
    lists: dict[str, ProblemList],
) -> None:
    for item in registry()["lists"]:
        assert lists[item["id"]].size == item["size"], item["id"]
        assert lists[item["id"]].name == item["name"], item["id"]


def test_each_list_records_where_it_came_from(lists: dict[str, ProblemList]) -> None:
    site = registry()["site_data"]
    for item in registry()["lists"]:
        source = lists[item["id"]].source
        assert source["kind"] == item["kind"], item["id"]
        assert source["retrieved_on"] == "2026-10-29", item["id"]
        assert "no problem text" in source["note"], item["id"]
        if item["kind"] == "leetcode_study_plan":
            assert source["plan_slug"] == item["plan_slug"]
            assert (
                source["url"] == f"https://leetcode.com/studyplan/{item['plan_slug']}/"
            )
        else:
            assert source["flag"] == item["flag"]
            assert source["revision"] == site["revision"]
            assert source["license"] == site["license"] == "MIT"
            assert site["revision"] in source["url"]


def test_the_site_data_revision_is_the_one_the_references_are_pinned_to() -> None:
    manifest = json.loads(
        (
            REPO_ROOT
            / "references"
            / "manifests"
            / "neetcode-leetcode-0001-two-sum-python.json"
        ).read_text(encoding="utf-8")
    )
    assert (
        registry()["site_data"]["revision"]
        == manifest["evidence"]["publication"]["revision"]
    )


def test_list_files_hold_ids_and_slugs_only() -> None:
    for path in DEFAULT_LISTS_DIR.glob("*.json"):
        data = json.loads(path.read_text(encoding="utf-8"))
        assert not FORBIDDEN_KEYS & set(data), path.name
        for group in data["groups"]:
            assert set(group) == {"name", "problems"}, path.name
            for problem in group["problems"]:
                assert set(problem) == {"id", "slug"}, path.name


def test_the_file_names_are_the_list_ids() -> None:
    for item in registry()["lists"]:
        assert (DEFAULT_LISTS_DIR / f"{item['id']}.json").is_file()
    assert sorted(p.name for p in DEFAULT_LISTS_DIR.iterdir()) == sorted(
        f"{item['id']}.json" for item in registry()["lists"]
    )


def test_premium_problems_are_kept_not_dropped(lists: dict[str, ProblemList]) -> None:
    blind = lists["blind-75"]
    assert sum(p.paid_only for p in blind.problems) == 6
    assert sum(p.paid_only for p in lists["neetcode-150"].problems) == 7
    assert all(not p.paid_only for p in lists["top-interview-150"].problems)


def test_the_starter_problems_appear_in_the_lists_that_publish_them(
    lists: dict[str, ProblemList],
) -> None:
    def ids(name: str) -> set[int]:
        return {p.frontend_question_id for p in lists[name].problems}

    assert {1, 217, 242, 20, 121} <= ids("blind-75")
    assert {1, 217, 242, 20, 121, 704} <= ids("neetcode-150")
    assert {1, 217, 242, 20, 121, 704} <= ids("neetcode-all")


def test_no_two_lists_share_a_file(tmp_path: Path) -> None:
    hashes = {p.read_bytes() for p in DEFAULT_LISTS_DIR.glob("*.json")}
    assert len(hashes) == len(list(DEFAULT_LISTS_DIR.glob("*.json")))
