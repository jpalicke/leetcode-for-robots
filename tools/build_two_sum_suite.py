# ABOUTME: Builds problems/leetcode-1/tests.json from hand-picked and seeded cases.
# ABOUTME: A brute-force pair counter is the oracle; every case must have one answer.

import argparse
import json
import random
import sys
from pathlib import Path
from typing import Any

SEED = 20261028
SUITE_VERSION = "leetcode-1-v1"
LIMIT = 10**9  # LeetCode bounds both nums[i] and target by this magnitude.
MAX_LENGTH = 10**4
REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT = REPO_ROOT / "problems" / "leetcode-1" / "tests.json"
MAX_ATTEMPTS = 10_000

# (id, nums, target). The answer is never written here; the oracle finds it.
HAND_CASES: tuple[tuple[str, list[int], int], ...] = (
    ("example-ascending", [1, 4, 6, 9], 13),
    ("example-unsorted", [8, 3, 5, 1], 6),
    ("minimum-length", [4, 9], 13),
    ("duplicate-pair-only", [3, 3], 6),
    ("duplicate-pair-in-the-middle", [1, 5, 5, 2], 10),
    ("duplicate-pair-with-other-values", [7, 2, 9, 2, 11], 4),
    ("half-of-target-appears-once", [6, 4, 8, 1], 12),
    ("half-of-target-appears-first", [5, 1, 9, 2], 10),
    ("all-negative", [-7, -3, -9, -1], -12),
    ("mixed-signs", [-4, 10, 6, 3], 6),
    ("zero-target", [7, -7, 2, 5], 0),
    ("zeros-sum-to-zero", [0, 4, 3, 0], 0),
    ("zero-is-one-operand", [0, 8, 5], 5),
    ("negative-target-with-positives", [14, -20, 9, 3, 30], 10),
    ("pair-at-the-start", [2, 9, 40, 51, 60], 11),
    ("pair-at-the-end", [40, 51, 60, 2, 9], 11),
    ("pair-first-and-last", [5, 40, 51, 60, 6], 11),
    ("order-descending", [95, 70, 50, 30, 10], 105),
    ("extreme-values-cancel", [LIMIT, -LIMIT, 7, 3], 0),
    ("extreme-negative-target", [0, -LIMIT, 17], -LIMIT),
    ("extreme-positive-target", [LIMIT, 0, 17], LIMIT),
    ("large-values-near-the-limit", [999_999_999, 1, 500_000_001, 400_000_000], LIMIT),
    ("adjacent-values-differ-by-one", [10, 11, 12, 13, 14], 27),
)


def find_pairs(nums: list[int], target: int) -> list[tuple[int, int]]:
    """Brute-force oracle: every pair of distinct positions that adds up to target."""
    return [
        (i, j)
        for i in range(len(nums))
        for j in range(i + 1, len(nums))
        if nums[i] + nums[j] == target
    ]


def count_pairs(nums: list[int], target: int) -> int:
    """Linear-time pair counter, used only for lengths too big to brute force."""
    counts: dict[int, int] = {}
    for value in nums:
        counts[value] = counts.get(value, 0) + 1
    total = 0
    for value, count in counts.items():
        other = target - value
        if other == value:
            total += count * (count - 1) // 2
        elif other > value and other in counts:
            total += count * counts[other]
    return total


def case_from(case_id: str, nums: list[int], target: int) -> dict[str, Any]:
    if not (2 <= len(nums) <= MAX_LENGTH):
        raise ValueError(f"{case_id}: length {len(nums)} breaks the constraints")
    if any(abs(value) > LIMIT for value in nums) or abs(target) > LIMIT:
        raise ValueError(f"{case_id}: a value breaks the constraints")
    pairs = find_pairs(nums, target)
    if len(pairs) != 1:
        raise ValueError(f"{case_id}: {len(pairs)} valid pairs, expected exactly one")
    return {"id": case_id, "args": [nums, target], "expected": list(pairs[0])}


def random_case(
    rng: random.Random, case_id: str, length: int, low: int, high: int
) -> dict[str, Any]:
    """Draw random arrays until exactly one pair adds up to a chosen target."""
    for _ in range(MAX_ATTEMPTS):
        nums = [rng.randint(low, high) for _ in range(length)]
        first, second = rng.sample(range(length), 2)
        target = nums[first] + nums[second]
        if abs(target) <= LIMIT and len(find_pairs(nums, target)) == 1:
            return case_from(case_id, nums, target)
    raise RuntimeError(f"{case_id}: no unique case found; widen the value range")


def performance_case(
    rng: random.Random, case_id: str, low: int, high: int
) -> dict[str, Any]:
    """Maximum length, all values distinct, with the only pair in the last two spots."""
    for _ in range(MAX_ATTEMPTS):
        values = rng.sample(range(low, high + 1), MAX_LENGTH)
        target = values[-1] + values[-2]
        if abs(target) <= LIMIT and count_pairs(values, target) == 1:
            return {
                "id": case_id,
                "args": [values, target],
                "expected": [MAX_LENGTH - 2, MAX_LENGTH - 1],
            }
    raise RuntimeError(f"{case_id}: no unique pair found; change the range")


def build_suite() -> dict[str, Any]:
    rng = random.Random(SEED)
    cases = [case_from(*hand) for hand in HAND_CASES]
    for number in range(1, 31):
        cases.append(
            random_case(
                rng, f"generated-small-{number:02d}", rng.randint(2, 8), -12, 12
            )
        )
    for number in range(1, 11):
        cases.append(
            random_case(
                rng,
                f"generated-medium-{number:02d}",
                rng.randint(50, 300),
                -(10**6),
                10**6,
            )
        )
    for number in range(1, 7):
        cases.append(
            random_case(
                rng,
                f"generated-wide-{number:02d}",
                rng.randint(20, 200),
                -LIMIT // 2,
                LIMIT // 2,
            )
        )
    cases.append(
        performance_case(rng, "performance-pair-at-the-end", -LIMIT // 2, LIMIT // 2)
    )
    cases.append(performance_case(rng, "performance-extreme-magnitudes", -LIMIT, LIMIT))
    return {
        "version": SUITE_VERSION,
        "seed": SEED,
        "generator": "tools/build_two_sum_suite.py",
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
    parser = argparse.ArgumentParser(description="Build the Two Sum test suite.")
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
    args.output.write_text(text, encoding="utf-8", newline="\n")
    print(f"wrote {len(json.loads(text)['cases'])} cases to {args.output}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
