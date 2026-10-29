# ABOUTME: Tests strict translation of every upstream catalog response row.
# ABOUTME: Uses real snapshot entries with distinct frontend and internal identities.


import pytest

from practice.catalog import CatalogError
from practice.catalog_refresh import parse_response
from tools.catalog_test_data import payload


def test_all_rows_and_both_ids_survive() -> None:
    data = payload()
    parsed = parse_response(data, "https://leetcode.com/api/problems/all/")
    assert len(parsed.entries) == len(data["stat_status_pairs"]) > 0
    assert any(e.frontend_question_id != e.question_id for e in parsed.entries)
    assert any(e.paid_only for e in parsed.entries)


@pytest.mark.parametrize("value", [True, "1", 1.5, 0, None])
@pytest.mark.parametrize("field", ["frontend_question_id", "question_id"])
def test_ids_are_never_coerced(field: str, value: object) -> None:
    data = payload()
    data["stat_status_pairs"][0]["stat"][field] = value
    with pytest.raises(CatalogError, match=field):
        parse_response(data, "https://example.org/")


@pytest.mark.parametrize("value", [True, "1", 1.5, 0, 4, None])
def test_difficulty_is_strict(value: object) -> None:
    data = payload()
    data["stat_status_pairs"][0]["difficulty"]["level"] = value
    with pytest.raises(CatalogError, match="difficulty"):
        parse_response(data, "https://example.org/")


@pytest.mark.parametrize(
    "data", [{}, {"stat_status_pairs": []}, {"stat_status_pairs": [None]}]
)
def test_empty_or_malformed_response_refused(data: object) -> None:
    with pytest.raises(CatalogError):
        parse_response(data, "https://example.org/")


@pytest.mark.parametrize("case", ["bool", "string", "float", "zero", "fewer", "more"])
def test_declared_total_must_match_all_rows(case: str) -> None:
    data = payload()
    count = len(data["stat_status_pairs"])
    data["num_total"] = {
        "bool": True,
        "string": str(count),
        "float": float(count),
        "zero": 0,
        "fewer": count - 1,
        "more": count + 1,
    }[case]
    with pytest.raises(CatalogError, match="num_total"):
        parse_response(data, "https://example.org/")


def test_declared_total_accepts_matching_integer() -> None:
    data = payload()
    data["num_total"] = len(data["stat_status_pairs"])
    assert (
        len(parse_response(data, "https://example.org/").entries) == data["num_total"]
    )


@pytest.mark.parametrize("field", ["error", "errors"])
def test_explicit_endpoint_errors_are_not_published(field: str) -> None:
    data = payload()
    data[field] = ["upstream rejected the request"]
    with pytest.raises(CatalogError, match="error"):
        parse_response(data, "https://example.org/")
