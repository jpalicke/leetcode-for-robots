# ABOUTME: Unit tests for catalog search ordering, run against the real snapshot.
# ABOUTME: Covers ID, slug and title matching and the no-match case.

from practice.catalog import DEFAULT_CATALOG_PATH, load_catalog
from practice.search import search

CATALOG = load_catalog(DEFAULT_CATALOG_PATH)


def titles(query: str) -> list[str]:
    return [entry.title for entry in search(CATALOG, query)]


def test_id_finds_exactly_one_entry() -> None:
    assert titles("1") == ["Two Sum"]


def test_id_wins_over_titles_containing_the_digits() -> None:
    assert len(search(CATALOG, "15")) == 1


def test_slug_matches_exactly() -> None:
    assert titles("two-sum") == ["Two Sum"]


def test_title_fragment_is_case_insensitive_and_exact_title_comes_first() -> None:
    found = titles("two sum")

    assert found[0] == "Two Sum"
    assert "Two Sum II - Input Array Is Sorted" in found
    assert all("two sum" in title.lower() for title in found)


def test_surrounding_whitespace_is_ignored() -> None:
    assert titles("  TWO SUM ") == titles("two sum")


def test_title_matches_after_the_exact_title_are_ordered_by_id() -> None:
    found = search(CATALOG, "sum")
    ids = [entry.frontend_question_id for entry in found]

    assert ids == sorted(ids)


def test_nothing_matches_gibberish_or_unknown_id() -> None:
    assert search(CATALOG, "zzzzqqqq-no-such-problem") == []
    assert search(CATALOG, "99999999") == []


def test_blank_query_matches_nothing() -> None:
    assert search(CATALOG, "   ") == []
