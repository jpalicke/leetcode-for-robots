# ABOUTME: Named output checkers that decide whether a solution's answer is acceptable.
# ABOUTME: Supports exact, any_order, any_of and a Two Sum style index predicate.

import json
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any, Literal

VerdictKind = Literal["passed", "failed", "malformed"]
PASSED = "passed"


@dataclass(frozen=True)
class Verdict:
    kind: VerdictKind
    detail: str = ""


@dataclass(frozen=True)
class Checker:
    """How a named checker judges one answer.

    expects says what a case's "expected" field must hold: "none" for a
    predicate that works from the arguments alone, "value" for any JSON value
    and "list" for a JSON list.
    """

    name: str
    expects: Literal["none", "value", "list"]
    check: Callable[[object, object, list[Any]], Verdict]


def _same(actual: object, expected: object) -> bool:
    """JSON equality that keeps True distinct from 1 and 0."""
    if isinstance(actual, bool) or isinstance(expected, bool):
        return (
            isinstance(actual, bool)
            and isinstance(expected, bool)
            and (actual == expected)
        )
    if isinstance(actual, list) and isinstance(expected, list):
        return len(actual) == len(expected) and all(
            _same(a, e) for a, e in zip(actual, expected, strict=True)
        )
    if isinstance(actual, dict) and isinstance(expected, dict):
        return actual.keys() == expected.keys() and all(
            _same(actual[key], expected[key]) for key in actual
        )
    if isinstance(actual, int | float) and isinstance(expected, int | float):
        return actual == expected
    return type(actual) is type(expected) and actual == expected


def _canonical(value: object) -> str:
    return json.dumps(value, sort_keys=True)


def _show(value: object) -> str:
    return json.dumps(value)


def _check_exact(actual: object, expected: object, args: list[Any]) -> Verdict:
    if _same(actual, expected):
        return Verdict("passed")
    return Verdict("failed", f"got {_show(actual)}, expected {_show(expected)}")


def _check_any_order(actual: object, expected: object, args: list[Any]) -> Verdict:
    if not isinstance(actual, list):
        return Verdict("malformed", f"expected a list, got {_show(actual)}")
    if not isinstance(expected, list):
        return Verdict("failed", "the suite's expected value is not a list")
    if sorted(map(_canonical, actual)) == sorted(map(_canonical, expected)):
        return Verdict("passed")
    return Verdict(
        "failed",
        f"got {_show(actual)}, expected the same items as {_show(expected)} "
        "in any order",
    )


def _check_any_of(actual: object, expected: object, args: list[Any]) -> Verdict:
    options = expected if isinstance(expected, list) else []
    if any(_same(actual, option) for option in options):
        return Verdict("passed")
    return Verdict("failed", f"got {_show(actual)}, expected one of {_show(options)}")


def _is_index(value: object) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


def _check_indices_sum_to_target(
    actual: object, expected: object, args: list[Any]
) -> Verdict:
    if not (
        isinstance(actual, list) and len(actual) == 2 and all(map(_is_index, actual))
    ):
        return Verdict(
            "malformed", f"expected two integer indices, got {_show(actual)}"
        )
    nums, target = args[0], args[1]
    first, second = actual
    if not (0 <= first < len(nums) and 0 <= second < len(nums)):
        return Verdict("failed", f"indices {actual} are outside 0..{len(nums) - 1}")
    if first == second:
        return Verdict("failed", f"indices {actual} reuse the same element")
    total = nums[first] + nums[second]
    if total != target:
        return Verdict(
            "failed",
            f"indices {actual} add up to {total}, not the target {target}",
        )
    return Verdict("passed")


CHECKERS: dict[str, Checker] = {
    checker.name: checker
    for checker in (
        Checker("exact", "value", _check_exact),
        Checker("any_order", "list", _check_any_order),
        Checker("any_of", "list", _check_any_of),
        Checker("indices_sum_to_target", "none", _check_indices_sum_to_target),
    )
}
