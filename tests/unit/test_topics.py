# ABOUTME: Checks loading and validating the dated category and topic facts per problem.
# ABOUTME: They must cover the catalog exactly, in a fixed order, or be rejected.

import copy
import json
from pathlib import Path
from typing import Any

import pytest

from practice.catalog import Catalog, parse_catalog
from practice.topics import TopicsError, load_topics, parse_topics

CATALOG_DATA: dict[str, Any] = {
    "platform": "leetcode",
    "source_url": "https://leetcode.com/api/problems/all/",
    "fetched_on": "2026-10-28",
    "entries": [
        {
            "platform": "leetcode",
            "frontend_question_id": n,
            "question_id": n,
            "title": f"Problem {n}",
            "slug": f"problem-{n}",
            "difficulty": "easy",
            "paid_only": False,
        }
        for n in range(1, 4)
    ],
}
TOPICS_DATA: dict[str, Any] = {
    "schema_version": 1,
    "platform": "leetcode",
    "source_url": "https://leetcode.com/graphql",
    "fetched_on": "2026-10-29",
    "note": "Category and topic tag slugs only; no problem text.",
    "entries": [
        {"id": 1, "categories": ["algorithms"], "topics": ["array", "hash-table"]},
        {"id": 2, "categories": ["database", "pandas"], "topics": ["database"]},
        {"id": 3, "categories": ["algorithms"], "topics": []},
    ],
}


@pytest.fixture
def catalog() -> Catalog:
    return parse_catalog(CATALOG_DATA)


def changed(change: Any) -> dict[str, Any]:
    data = copy.deepcopy(TOPICS_DATA)
    change(data)
    return data


def test_valid_facts_are_loaded_by_problem_number(catalog: Catalog) -> None:
    topics = parse_topics(TOPICS_DATA, catalog)
    assert topics.fetched_on == "2026-10-29"
    assert topics.facts[1].categories == ("algorithms",)
    assert topics.facts[1].topics == ("array", "hash-table")
    assert topics.facts[2].categories == ("database", "pandas")
    assert topics.facts[3].topics == ()


@pytest.mark.parametrize(
    ("change", "message"),
    [
        (lambda d: d.update(schema_version=2), "schema_version"),
        (lambda d: d.update(platform="other"), "platform"),
        (lambda d: d.update(source_url="http://x.test"), "https"),
        (lambda d: d.update(fetched_on="today"), "fetched_on"),
        (lambda d: d.update(extra=1), "unknown"),
        (lambda d: d.update(entries=[]), "entries must be a non-empty list"),
        (lambda d: d["entries"][0].update(id="1"), "id must be"),
        (lambda d: d["entries"][0].update(id=True), "id must be"),
        (lambda d: d["entries"][0].update(categories=[]), "categories"),
        (lambda d: d["entries"][0].update(categories=["nonsense"]), "unknown category"),
        (lambda d: d["entries"][0].update(categories=["pandas", "database"]), "sorted"),
        (lambda d: d["entries"][0].update(topics=["hash-table", "array"]), "sorted"),
        (lambda d: d["entries"][0].update(topics=["array", "array"]), "sorted"),
        (lambda d: d["entries"][0].update(topics=["Array"]), "topic"),
        (lambda d: d["entries"][0].update(topics="array"), "topics"),
        (lambda d: d["entries"][0].update(extra=1), "unknown"),
        (lambda d: d["entries"][1].update(id=1), "appears more than once"),
        (lambda d: d["entries"][2].update(id=99), "problem 99 is not in the catalog"),
        (lambda d: d["entries"].pop(), "no facts for problem 3"),
    ],
)
def test_bad_facts_are_rejected_with_a_clear_message(
    catalog: Catalog, change: Any, message: str
) -> None:
    with pytest.raises(TopicsError, match=message):
        parse_topics(changed(change), catalog)


def test_a_file_loads_and_an_invalid_one_names_itself(
    catalog: Catalog, tmp_path: Path
) -> None:
    good = tmp_path / "topics.json"
    good.write_text(json.dumps(TOPICS_DATA), encoding="utf-8")
    assert load_topics(good, catalog).facts[1].topics == ("array", "hash-table")
    bad = tmp_path / "bad.json"
    bad.write_text(json.dumps(changed(lambda d: d.update(fetched_on="x"))), "utf-8")
    with pytest.raises(TopicsError, match=r"bad\.json is invalid"):
        load_topics(bad, catalog)


def test_unreadable_and_truncated_files_are_topics_errors(
    catalog: Catalog, tmp_path: Path
) -> None:
    with pytest.raises(TopicsError, match="cannot read"):
        load_topics(tmp_path / "missing.json", catalog)
    cut = tmp_path / "cut.json"
    cut.write_text(json.dumps(TOPICS_DATA)[:60], encoding="utf-8")
    with pytest.raises(TopicsError, match=r"cut\.json is not valid JSON"):
        load_topics(cut, catalog)
