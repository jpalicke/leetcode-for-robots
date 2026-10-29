# ABOUTME: Checks how a package declares a probe budget and how the limit is computed.
# ABOUTME: Bad declarations are rejected when the package loads, with a clear message.

import json
from collections.abc import Callable
from pathlib import Path
from typing import Any

import pytest

from practice.package import PackageError, ProbeBudget, load_package

BASE: dict[str, Any] = {
    "platform": "fixture",
    "id": "search-fixture",
    "title": "Search",
    "language": "python",
    "callable": {
        "adapter": "function",
        "name": "search",
        "parameters": ["nums", "target"],
    },
    "checker": "exact",
}
SUITE: dict[str, Any] = {
    "version": "fixture-1",
    "cases": [{"id": "one", "args": [[1, 2, 3], 2], "expected": 1}],
}
BUDGET = {"argument": "nums", "growth": "log2", "slack": 2}


def with_budget(budget: object) -> dict[str, Any]:
    return {**BASE, "probe_budget": budget}


def test_a_package_without_a_budget_has_none(
    make_package: Callable[..., Path],
) -> None:
    assert load_package(make_package(BASE, SUITE)).probe_budget is None


def test_a_declared_budget_is_loaded(make_package: Callable[..., Path]) -> None:
    package = load_package(make_package(with_budget(BUDGET), SUITE))
    assert package.probe_budget == ProbeBudget(
        argument="nums", argument_index=0, growth="log2", slack=2
    )


def test_the_argument_index_follows_the_parameter_order(
    make_package: Callable[..., Path],
) -> None:
    metadata = {
        **BASE,
        "callable": {**BASE["callable"], "parameters": ["target", "nums"]},
        "probe_budget": BUDGET,
    }
    suite = {
        "version": "fixture-1",
        "cases": [{"id": "one", "args": [2, [1, 2, 3]], "expected": 1}],
    }
    package = load_package(make_package(metadata, suite))
    assert package.probe_budget is not None
    assert package.probe_budget.argument_index == 1


def test_slack_defaults_to_two(make_package: Callable[..., Path]) -> None:
    metadata = with_budget({"argument": "nums", "growth": "log2"})
    package = load_package(make_package(metadata, SUITE))
    assert package.probe_budget is not None
    assert package.probe_budget.slack == 2


@pytest.mark.parametrize(
    ("length", "limit"),
    [(1, 3), (2, 4), (3, 4), (4, 5), (7, 5), (8, 6), (1_000, 12), (10_000, 16)],
)
def test_the_limit_is_the_bit_length_of_the_size_plus_slack(
    length: int, limit: int
) -> None:
    budget = ProbeBudget(argument="nums", argument_index=0, growth="log2", slack=2)
    assert budget.limit(length) == limit


def test_the_limit_matches_the_most_a_binary_search_can_read() -> None:
    """ceil(log2(n + 1)) steps suffice, and that equals n.bit_length()."""
    import math

    for length in range(1, 5_000):
        assert length.bit_length() == math.ceil(math.log2(length + 1))


def test_slack_is_added_to_the_limit() -> None:
    budget = ProbeBudget(argument="nums", argument_index=0, growth="log2", slack=0)
    assert budget.limit(10_000) == 14
    assert ProbeBudget("nums", 0, "log2", 5).limit(10_000) == 19


@pytest.mark.parametrize(
    ("budget", "message"),
    [
        ("log2", "probe_budget must be an object"),
        ([], "probe_budget must be an object"),
        ({"growth": "log2"}, "probe_budget argument"),
        ({"argument": "", "growth": "log2"}, "probe_budget argument"),
        ({"argument": "missing", "growth": "log2"}, "not a parameter"),
        ({"argument": "nums"}, "probe_budget growth"),
        ({"argument": "nums", "growth": "linear"}, "probe_budget growth"),
        ({"argument": "nums", "growth": "log2", "slack": -1}, "probe_budget slack"),
        ({"argument": "nums", "growth": "log2", "slack": 1.5}, "probe_budget slack"),
        ({"argument": "nums", "growth": "log2", "slack": True}, "probe_budget slack"),
        ({"argument": "nums", "growth": "log2", "extra": 1}, "unknown"),
    ],
)
def test_a_bad_declaration_is_rejected_when_the_package_loads(
    make_package: Callable[..., Path], budget: object, message: str
) -> None:
    with pytest.raises(PackageError, match=message):
        load_package(make_package(with_budget(budget), SUITE))


def test_the_budget_is_part_of_the_suite_hash(
    make_package: Callable[..., Path], tmp_path: Path
) -> None:
    plain = load_package(make_package(BASE, SUITE))
    budgeted_dir = tmp_path / "budgeted"
    budgeted_dir.mkdir()
    (budgeted_dir / "problem.json").write_text(
        json.dumps(with_budget(BUDGET)), encoding="utf-8"
    )
    (budgeted_dir / "tests.json").write_text(json.dumps(SUITE), encoding="utf-8")
    budgeted = load_package(budgeted_dir)
    assert plain.suite_sha256 != budgeted.suite_sha256  # So old evidence goes stale.


def test_changing_the_slack_changes_the_suite_hash(tmp_path: Path) -> None:
    hashes = set()
    for slack in (1, 2, 3):
        directory = tmp_path / f"slack-{slack}"
        directory.mkdir()
        metadata = with_budget({**BUDGET, "slack": slack})
        (directory / "problem.json").write_text(json.dumps(metadata), encoding="utf-8")
        (directory / "tests.json").write_text(json.dumps(SUITE), encoding="utf-8")
        hashes.add(load_package(directory).suite_sha256)
    assert len(hashes) == 3


@pytest.mark.parametrize("bad", ["abc", 7, None, {"a": 1}])
def test_a_budgeted_argument_must_be_a_list_in_every_case(
    make_package: Callable[..., Path], bad: object
) -> None:
    suite = {
        "version": "fixture-1",
        "cases": [
            {"id": "fine", "args": [[1, 2, 3], 2], "expected": 1},
            {"id": "broken", "args": [bad, 2], "expected": -1},
        ],
    }
    with pytest.raises(PackageError, match="broken.*nums.*must be a list"):
        load_package(make_package(with_budget(BUDGET), suite))


def test_a_list_valued_argument_without_a_budget_is_not_checked(
    make_package: Callable[..., Path],
) -> None:
    suite = {
        "version": "fixture-1",
        "cases": [{"id": "text", "args": ["abc", 2], "expected": -1}],
    }
    assert load_package(make_package(BASE, suite)).suite is not None
