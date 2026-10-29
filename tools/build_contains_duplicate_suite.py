# ABOUTME: Builds problems/leetcode-217/tests.json from hand-picked and seeded cases.
# ABOUTME: A sorted-neighbour check is the oracle; the answer is never written by hand.

import argparse
import json
import random
import sys
from pathlib import Path
from typing import Any

SEED = 20261029
SUITE_VERSION = "leetcode-217-v2"
LIMIT = 10**9  # Bound on |nums[i]| (assumed from the published constraints).
MAX_LENGTH = 10**5
PERFORMANCE_SPAN = 10**5
REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT = REPO_ROOT / "problems" / "leetcode-217" / "tests.json"

# (id, nums). The answer is never written here; the oracle finds it.
HAND_CASES: tuple[tuple[str, list[int]], ...] = (
    # The three examples listed on the problem page, as the owner reported them.
    ("platform-example-1", [1, 2, 3, 1]),
    ("platform-example-2", [1, 2, 3, 4]),
    ("platform-example-3", [1, 1, 1, 3, 3, 4, 3, 2, 4, 2]),
    ("example-repeat", [5, 8, 2, 8]),
    ("example-all-different", [4, 9, 1, 7]),
    ("single-element", [42]),
    ("two-equal", [6, 6]),
    ("two-different", [6, 7]),
    ("repeat-at-the-start", [3, 3, 9, 4, 8]),
    ("repeat-at-the-end", [9, 4, 8, 3, 3]),
    ("repeat-first-and-last", [3, 9, 4, 8, 3]),
    ("repeat-far-apart", [7, 1, 2, 3, 4, 5, 6, 8, 9, 7]),
    ("adjacent-repeat", [1, 2, 5, 5, 3]),
    ("all-equal", [4, 4, 4, 4, 4]),
    ("one-value-three-times", [2, 9, 2, 5, 2]),
    ("two-different-repeats", [1, 2, 1, 2]),
    ("sorted-ascending-no-repeat", [1, 2, 3, 4, 5, 6]),
    ("sorted-descending-no-repeat", [60, 50, 40, 30, 20, 10]),
    ("sorted-ascending-repeat-in-the-middle", [1, 2, 3, 3, 4, 5]),
    ("opposite-signs-are-different", [5, -5, 7, -7]),
    ("opposite-signs-then-a-real-repeat", [5, -5, 7, -7, 5]),
    ("negative-repeat", [-8, 3, -8, 1]),
    ("all-negative-no-repeat", [-1, -2, -3, -4]),
    ("zero-repeat", [0, 4, 0]),
    ("zero-once", [0, 4, -4]),
    ("extreme-repeat", [LIMIT, 3, LIMIT]),
    ("extreme-negative-repeat", [-LIMIT, 3, -LIMIT]),
    ("extreme-values-all-different", [LIMIT, -LIMIT, 0, LIMIT - 1, -LIMIT + 1]),
    ("neighbouring-values-all-different", [10, 11, 12, 13, 14, 15]),
    ("repeat-only-in-the-last-pair", [8, 6, 7, 5, 3, 0, 9, 9]),
    ("repeat-only-in-the-first-pair", [9, 9, 8, 6, 7, 5, 3, 0]),
)


def has_duplicate(nums: list[int]) -> bool:
    """Oracle: after sorting, a repeated value sits next to its twin."""
    ordered = sorted(nums)
    return any(a == b for a, b in zip(ordered, ordered[1:], strict=False))


def case_from(case_id: str, nums: list[int]) -> dict[str, Any]:
    if not (1 <= len(nums) <= MAX_LENGTH):
        raise ValueError(f"{case_id}: length {len(nums)} breaks the constraints")
    if any(abs(value) > LIMIT for value in nums):
        raise ValueError(f"{case_id}: a value breaks the constraints")
    return {"id": case_id, "args": [nums], "expected": has_duplicate(nums)}


def distinct_values(rng: random.Random, length: int, low: int, high: int) -> list[int]:
    return rng.sample(range(low, high + 1), length)


def with_repeat(rng: random.Random, length: int, low: int, high: int) -> list[int]:
    """Distinct values with one of them copied over a different position."""
    values = distinct_values(rng, length, low, high)
    source, target = rng.sample(range(length), 2)
    values[target] = values[source]
    return values


def build_suite() -> dict[str, Any]:
    rng = random.Random(SEED)
    cases = [case_from(*hand) for hand in HAND_CASES]
    for number in range(1, 21):
        length = rng.randint(2, 8)
        cases.append(
            case_from(
                f"generated-small-{number:02d}",
                distinct_values(rng, length, -12, 12)
                if number % 2
                else with_repeat(rng, length, -12, 12),
            )
        )
    for number in range(1, 11):
        length = rng.randint(50, 400)
        cases.append(
            case_from(
                f"generated-medium-{number:02d}",
                distinct_values(rng, length, -(10**6), 10**6)
                if number % 2
                else with_repeat(rng, length, -(10**6), 10**6),
            )
        )
    for number in range(1, 9):
        length = rng.randint(20, 300)
        cases.append(
            case_from(
                f"generated-wide-{number:02d}",
                distinct_values(rng, length, -LIMIT, LIMIT)
                if number % 2
                else with_repeat(rng, length, -LIMIT, LIMIT),
            )
        )
    # Compact values keep the committed file small; the length is what matters here.
    cases.append(
        case_from(
            "performance-all-different",
            distinct_values(rng, MAX_LENGTH, -PERFORMANCE_SPAN, PERFORMANCE_SPAN),
        )
    )
    last_pair = distinct_values(rng, MAX_LENGTH, -PERFORMANCE_SPAN, PERFORMANCE_SPAN)
    last_pair[-1] = last_pair[-2]
    cases.append(case_from("performance-repeat-in-the-last-pair", last_pair))
    cases.append(case_from("performance-all-equal", [7] * MAX_LENGTH))
    return {
        "version": SUITE_VERSION,
        "seed": SEED,
        "generator": "tools/build_contains_duplicate_suite.py",
        "cases": cases,
    }


def render(suite: dict[str, Any]) -> str:
    """One case per line so a changed case shows up as a one-line diff."""
    lines = [
        "{",
        f'  "version": {json.dumps(suite["version"])},',
        f'  "seed": {suite["seed"]},',
        f'  "generator": {json.dumps(suite["generator"])},',
        '  "cases": [',
    ]
    body = [
        f"    {json.dumps(case, separators=(', ', ': '))}" for case in suite["cases"]
    ]
    lines.append(",\n".join(body))
    lines += ["  ]", "}", ""]
    return "\n".join(lines)


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description="Build the Contains Duplicate suite.")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument(
        "--check",
        action="store_true",
        help="exit 1 if the file differs from a fresh build instead of writing it",
    )
    args = parser.parse_args(argv)
    text = render(build_suite())
    if args.check:
        current = (
            args.output.read_text(encoding="utf-8") if args.output.exists() else ""
        )
        if current != text:
            print(f"{args.output} differs from a fresh build", file=sys.stderr)
            return 1
        print(f"{args.output} matches a fresh build")
        return 0
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(text, encoding="utf-8", newline="\n")
    print(f"wrote {len(json.loads(text)['cases'])} cases to {args.output}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
