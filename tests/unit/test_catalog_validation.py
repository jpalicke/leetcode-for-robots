# ABOUTME: Unit tests for catalog validation, driven by the real committed snapshot.
# ABOUTME: Each case damages one field of real data and expects a clear rejection.

import copy
import json
from collections.abc import Callable
from datetime import date
from typing import Any

import pytest

from practice.catalog import DEFAULT_CATALOG_PATH, CatalogError, parse_catalog


def real_data() -> dict[str, Any]:
    data: dict[str, Any] = json.loads(DEFAULT_CATALOG_PATH.read_text(encoding="utf-8"))
    return data


def test_real_snapshot_is_valid_and_complete() -> None:
    data = real_data()
    catalog = parse_catalog(data)

    assert catalog.platform == "leetcode"
    assert catalog.source_url == "https://leetcode.com/api/problems/all/"
    assert date.fromisoformat(catalog.fetched_on) <= date.today()
    assert len(catalog.entries) == len(data["entries"]) > 0


def test_frontend_and_internal_ids_stay_distinct() -> None:
    catalog = parse_catalog(real_data())

    differing = [
        entry
        for entry in catalog.entries
        if entry.frontend_question_id != entry.question_id
    ]
    assert differing, "the real snapshot has entries whose IDs differ"
    two_sum = next(e for e in catalog.entries if e.slug == "two-sum")
    assert (two_sum.frontend_question_id, two_sum.title) == (1, "Two Sum")
    assert two_sum.identity == ("leetcode", 1)


def damage_missing_title(data: dict[str, Any]) -> None:
    del data["entries"][3]["title"]


def damage_text_id(data: dict[str, Any]) -> None:
    data["entries"][3]["frontend_question_id"] = "4"


def damage_boolean_id(data: dict[str, Any]) -> None:
    data["entries"][3]["frontend_question_id"] = True


def damage_duplicate_id(data: dict[str, Any]) -> None:
    data["entries"][3]["frontend_question_id"] = data["entries"][2][
        "frontend_question_id"
    ]


def damage_duplicate_slug(data: dict[str, Any]) -> None:
    data["entries"][3]["slug"] = data["entries"][2]["slug"]


def damage_difficulty(data: dict[str, Any]) -> None:
    data["entries"][3]["difficulty"] = "impossible"


def damage_premium_flag(data: dict[str, Any]) -> None:
    data["entries"][3]["paid_only"] = "no"


def damage_entry_platform(data: dict[str, Any]) -> None:
    data["entries"][3]["platform"] = "hackerrank"


def damage_no_entries(data: dict[str, Any]) -> None:
    data["entries"] = []


def damage_entry_shape(data: dict[str, Any]) -> None:
    data["entries"][3] = "Two Sum"


def damage_fetch_date(data: dict[str, Any]) -> None:
    data["fetched_on"] = "yesterday"


def damage_source_url(data: dict[str, Any]) -> None:
    del data["source_url"]


@pytest.mark.parametrize(
    ("damage", "message"),
    [
        (damage_missing_title, "title"),
        (damage_text_id, "frontend_question_id"),
        (damage_boolean_id, "frontend_question_id"),
        (damage_duplicate_id, "duplicate frontend_question_id"),
        (damage_duplicate_slug, "duplicate slug"),
        (damage_difficulty, "difficulty"),
        (damage_premium_flag, "paid_only"),
        (damage_entry_platform, "platform"),
        (damage_no_entries, "entries"),
        (damage_entry_shape, "entry 3"),
        (damage_fetch_date, "fetched_on"),
        (damage_source_url, "source_url"),
    ],
)
def test_damaged_snapshot_is_rejected_with_a_clear_message(
    damage: Callable[[dict[str, Any]], None], message: str
) -> None:
    data = copy.deepcopy(real_data())
    damage(data)

    with pytest.raises(CatalogError, match=message):
        parse_catalog(data)


def test_top_level_must_be_an_object() -> None:
    with pytest.raises(CatalogError, match="JSON object"):
        parse_catalog([])
