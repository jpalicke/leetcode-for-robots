# ABOUTME: Checks loading and validating curated problem lists against a catalog.
# ABOUTME: Bad files are rejected with a message that names the file and the problem.

import copy
import json
from pathlib import Path
from typing import Any

import pytest

from practice.catalog import Catalog, parse_catalog
from practice.lists import ListError, load_list, load_lists, parse_list

CATALOG_DATA: dict[str, Any] = {
    "platform": "leetcode",
    "source_url": "https://leetcode.com/api/problems/all/",
    "fetched_on": "2026-10-28",
    "entries": [
        {
            "platform": "leetcode",
            "frontend_question_id": number,
            "question_id": number,
            "title": f"Problem {number}",
            "slug": f"problem-{number}",
            "difficulty": "easy",
            "paid_only": number == 3,
        }
        for number in range(1, 7)
    ],
}
LIST_DATA: dict[str, Any] = {
    "schema_version": 1,
    "id": "tiny-list",
    "name": "Tiny list",
    "platform": "leetcode",
    "size": 4,
    "source": {
        "kind": "neetcode_site_data",
        "url": "https://example.test/lists/tiny",
        "retrieved_on": "2026-10-29",
        "license": "MIT",
    },
    "groups": [
        {
            "name": "First group",
            "problems": [
                {"id": 2, "slug": "problem-2"},
                {"id": 1, "slug": "problem-1"},
            ],
        },
        {
            "name": "Second group",
            "problems": [
                {"id": 3, "slug": "problem-3"},
                {"id": 5, "slug": "problem-5"},
            ],
        },
    ],
}


@pytest.fixture
def catalog() -> Catalog:
    return parse_catalog(CATALOG_DATA)


def changed(change: Any) -> dict[str, Any]:
    data = copy.deepcopy(LIST_DATA)
    change(data)
    return data


def test_a_valid_list_keeps_its_order_and_groups(catalog: Catalog) -> None:
    result = parse_list(LIST_DATA, catalog)
    assert (result.list_id, result.name, result.size) == ("tiny-list", "Tiny list", 4)
    assert [g.name for g in result.groups] == ["First group", "Second group"]
    assert [p.frontend_question_id for p in result.problems] == [2, 1, 3, 5]


def test_each_problem_carries_the_catalog_facts(catalog: Catalog) -> None:
    result = parse_list(LIST_DATA, catalog)
    third = result.problems[2]
    assert (third.title, third.slug, third.difficulty) == (
        "Problem 3",
        "problem-3",
        "easy",
    )
    assert third.paid_only is True  # Premium problems stay in the list, flagged.
    assert result.problems[0].paid_only is False


def test_the_source_is_kept(catalog: Catalog) -> None:
    source = parse_list(LIST_DATA, catalog).source
    assert source["kind"] == "neetcode_site_data"
    assert source["retrieved_on"] == "2026-10-29"
    assert source["license"] == "MIT"


@pytest.mark.parametrize(
    ("change", "message"),
    [
        (lambda d: d.update(schema_version=2), "schema_version"),
        (lambda d: d.update(id="Bad Id"), "id must be"),
        (lambda d: d.update(id=""), "id must be"),
        (lambda d: d.update(name=""), "name must be"),
        (lambda d: d.update(platform="other"), "platform"),
        (lambda d: d.update(size=3), "declares 3 problems but has 4"),
        (lambda d: d.update(size=0), "size must be"),
        (lambda d: d.update(size=True), "size must be"),
        (lambda d: d.update(extra=1), "unknown"),
        (lambda d: d.pop("source"), "source"),
        (lambda d: d["source"].update(url="http://insecure.test/x"), "https"),
        (lambda d: d["source"].update(retrieved_on="yesterday"), "retrieved_on"),
        (lambda d: d["source"].pop("kind"), "kind"),
        (lambda d: d.update(groups=[]), "groups must be a non-empty list"),
        (lambda d: d["groups"][0].update(name=""), "group 0"),
        (lambda d: d["groups"][0].update(problems=[]), "group 0"),
        (lambda d: d["groups"][0]["problems"][0].update(id="2"), "id must be"),
        (lambda d: d["groups"][0]["problems"][0].update(id=True), "id must be"),
        (lambda d: d["groups"][0]["problems"][0].update(slug=""), "slug must be"),
        (lambda d: d["groups"][0]["problems"][0].update(extra=1), "unknown"),
    ],
)
def test_a_malformed_list_is_rejected_with_a_clear_message(
    catalog: Catalog, change: Any, message: str
) -> None:
    with pytest.raises(ListError, match=message):
        parse_list(changed(change), catalog)


def test_a_problem_missing_from_the_catalog_is_rejected(catalog: Catalog) -> None:
    def change(d: dict[str, Any]) -> None:
        d["groups"][0]["problems"][0] = {"id": 99, "slug": "problem-99"}

    with pytest.raises(ListError, match="problem 99 is not in the catalog"):
        parse_list(changed(change), catalog)


def test_a_slug_that_disagrees_with_the_catalog_is_rejected(catalog: Catalog) -> None:
    def change(d: dict[str, Any]) -> None:
        d["groups"][0]["problems"][0]["slug"] = "wrong-slug"

    with pytest.raises(ListError, match="problem 2 has slug 'wrong-slug'"):
        parse_list(changed(change), catalog)


def test_a_repeated_problem_in_one_list_is_rejected(catalog: Catalog) -> None:
    def change(d: dict[str, Any]) -> None:
        d["groups"][1]["problems"][0] = {"id": 2, "slug": "problem-2"}

    with pytest.raises(ListError, match="problem 2 appears more than once"):
        parse_list(changed(change), catalog)


def test_the_same_problem_may_appear_in_different_lists(
    catalog: Catalog, tmp_path: Path
) -> None:
    other = copy.deepcopy(LIST_DATA)
    other["id"] = "other-list"
    for name, data in (("tiny-list", LIST_DATA), ("other-list", other)):
        (tmp_path / f"{name}.json").write_text(json.dumps(data), encoding="utf-8")
    lists = load_lists(tmp_path, catalog)
    assert [item.list_id for item in lists] == ["other-list", "tiny-list"]


def test_load_list_reads_a_file(catalog: Catalog, tmp_path: Path) -> None:
    path = tmp_path / "tiny-list.json"
    path.write_text(json.dumps(LIST_DATA), encoding="utf-8")
    assert load_list(path, catalog).list_id == "tiny-list"


def test_an_unreadable_file_is_a_list_error(catalog: Catalog, tmp_path: Path) -> None:
    with pytest.raises(ListError, match="cannot read"):
        load_list(tmp_path / "missing.json", catalog)


def test_a_truncated_file_is_a_list_error_naming_the_file(
    catalog: Catalog, tmp_path: Path
) -> None:
    path = tmp_path / "tiny-list.json"
    path.write_text(json.dumps(LIST_DATA)[:80], encoding="utf-8")
    with pytest.raises(ListError, match=r"tiny-list\.json is not valid JSON"):
        load_list(path, catalog)


def test_an_invalid_list_error_names_the_file(catalog: Catalog, tmp_path: Path) -> None:
    path = tmp_path / "tiny-list.json"
    path.write_text(json.dumps(changed(lambda d: d.update(size=9))), encoding="utf-8")
    with pytest.raises(ListError, match=r"tiny-list\.json is invalid"):
        load_list(path, catalog)


def test_the_file_name_must_match_the_list_id(catalog: Catalog, tmp_path: Path) -> None:
    path = tmp_path / "another-name.json"
    path.write_text(json.dumps(LIST_DATA), encoding="utf-8")
    with pytest.raises(ListError, match="file name must be tiny-list.json"):
        load_list(path, catalog)


def test_one_bad_file_makes_the_whole_folder_fail(
    catalog: Catalog, tmp_path: Path
) -> None:
    (tmp_path / "tiny-list.json").write_text(json.dumps(LIST_DATA), encoding="utf-8")
    (tmp_path / "broken.json").write_text("{", encoding="utf-8")
    with pytest.raises(ListError, match=r"broken\.json"):
        load_lists(tmp_path, catalog)


def test_a_missing_folder_is_a_list_error(catalog: Catalog, tmp_path: Path) -> None:
    with pytest.raises(ListError, match="not a directory"):
        load_lists(tmp_path / "nowhere", catalog)


def test_an_empty_folder_gives_no_lists(catalog: Catalog, tmp_path: Path) -> None:
    assert load_lists(tmp_path, catalog) == ()


def test_files_that_are_not_json_are_ignored(catalog: Catalog, tmp_path: Path) -> None:
    (tmp_path / "tiny-list.json").write_text(json.dumps(LIST_DATA), encoding="utf-8")
    (tmp_path / "README.md").write_text("notes", encoding="utf-8")
    assert [item.list_id for item in load_lists(tmp_path, catalog)] == ["tiny-list"]
