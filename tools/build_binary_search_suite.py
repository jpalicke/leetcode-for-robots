# ABOUTME: Builds problems/leetcode-704/tests.json from hand-picked and seeded cases.
# ABOUTME: A plain linear lookup is the oracle; the answer is never written by hand.

import argparse
import json
import random
import sys
from pathlib import Path
from typing import Any

SEED = 20261029
SUITE_VERSION = "leetcode-704-v1"
MAX_LENGTH = 10**4
LOW, HIGH = -9999, 9999  # The page's bounds are strict: -10^4 < value < 10^4.
REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT = REPO_ROOT / "problems" / "leetcode-704" / "tests.json"

# (id, nums, target). The answer is never written here; the oracle finds it.
HAND_CASES: tuple[tuple[str, list[int], int], ...] = (
    # The two examples listed on the problem page.
    ("platform-example-1", [-1, 0, 3, 5, 9, 12], 9),
    ("platform-example-2", [-1, 0, 3, 5, 9, 12], 2),
    # Written for this project.
    ("single-element-found", [5], 5),
    ("single-element-missing-below", [5], 3),
    ("single-element-missing-above", [5], 8),
    ("two-elements-first", [1, 4], 1),
    ("two-elements-last", [1, 4], 4),
    ("two-elements-missing-between", [1, 4], 2),
    ("two-elements-missing-below", [1, 4], 0),
    ("two-elements-missing-above", [1, 4], 9),
    ("three-elements-first", [1, 5, 9], 1),
    ("three-elements-middle", [1, 5, 9], 5),
    ("three-elements-last", [1, 5, 9], 9),
    ("target-is-first", [2, 4, 6, 8, 10, 12, 14], 2),
    ("target-is-last", [2, 4, 6, 8, 10, 12, 14], 14),
    ("target-is-second", [1, 2, 3, 4, 5, 6, 7, 8], 2),
    ("target-is-second-from-last", [1, 2, 3, 4, 5, 6, 7, 8], 7),
    ("target-below-all", [10, 20, 30, 40], 5),
    ("target-above-all", [10, 20, 30, 40], 45),
    ("target-between-neighbours", [10, 20, 30, 40], 25),
    ("odd-length-exact-middle", [1, 3, 5, 7, 9], 5),
    ("even-length-lower-middle", [1, 3, 5, 7], 3),
    ("even-length-upper-middle", [1, 3, 5, 7], 5),
    ("all-negative-found", [-90, -70, -50, -30, -10], -50),
    ("all-negative-missing", [-90, -70, -50, -30, -10], -60),
    ("zero-found", [-3, -1, 0, 2, 4], 0),
    ("zero-missing", [-3, -1, 1, 2, 4], 0),
    ("extreme-low-found", [-9999, -5, 0, 5, 9999], -9999),
    ("extreme-high-found", [-9999, -5, 0, 5, 9999], 9999),
    ("extreme-low-missing", [-9998, -5, 0, 5, 9999], -9999),
    ("extreme-high-missing", [-9999, -5, 0, 5, 9998], 9999),
    ("consecutive-values-found", [10, 11, 12, 13, 14, 15], 13),
    ("consecutive-values-missing-just-above", [10, 11, 12, 13, 14, 15], 16),
    ("consecutive-values-missing-just-below", [10, 11, 12, 13, 14, 15], 9),
    ("wide-gaps-missing", [-9000, -3000, 0, 3000, 9000], 2999),
    ("wide-gaps-found", [-9000, -3000, 0, 3000, 9000], -3000),
)


def position_of(nums: list[int], target: int) -> int:
    """Oracle: a plain linear lookup. It does not halve anything."""
    return nums.index(target) if target in nums else -1


def case_from(case_id: str, nums: list[int], target: int) -> dict[str, Any]:
    if not (1 <= len(nums) <= MAX_LENGTH):
        raise ValueError(f"{case_id}: length {len(nums)} breaks the constraints")
    if any(not (LOW <= value <= HIGH) for value in nums) or not (LOW <= target <= HIGH):
        raise ValueError(f"{case_id}: a value breaks the constraints")
    if any(a >= b for a, b in zip(nums, nums[1:], strict=False)):
        raise ValueError(f"{case_id}: nums must be strictly ascending")
    return {
        "id": case_id,
        "args": [nums, target],
        "expected": position_of(nums, target),
    }


def sorted_unique(rng: random.Random, length: int, low: int, high: int) -> list[int]:
    return sorted(rng.sample(range(low, high + 1), length))


def absent_value(rng: random.Random, nums: list[int], low: int, high: int) -> int:
    present = set(nums)
    while True:
        candidate = rng.randint(low, high)
        if candidate not in present:
            return candidate


def random_case(
    rng: random.Random, case_id: str, length: int, low: int, high: int, found: bool
) -> dict[str, Any]:
    nums = sorted_unique(rng, length, low, high)
    target = rng.choice(nums) if found else absent_value(rng, nums, low, high)
    return case_from(case_id, nums, target)


def build_suite() -> dict[str, Any]:
    rng = random.Random(SEED)
    cases = [case_from(*hand) for hand in HAND_CASES]
    for number in range(1, 31):
        cases.append(
            random_case(
                rng,
                f"generated-small-{number:02d}",
                rng.randint(1, 9),
                -20,
                20,
                number % 2 == 1,
            )
        )
    for number in range(1, 15):
        cases.append(
            random_case(
                rng,
                f"generated-medium-{number:02d}",
                rng.randint(50, 500),
                LOW,
                HIGH,
                number % 2 == 1,
            )
        )
    for number in range(1, 9):
        cases.append(
            random_case(
                rng,
                f"generated-wide-{number:02d}",
                rng.randint(1000, 4000),
                LOW,
                HIGH,
                number % 2 == 1,
            )
        )
    # Maximum length. Several targets so no fixed probe position is always right.
    full = sorted_unique(rng, MAX_LENGTH, LOW + 1, HIGH - 1)  # Both extremes absent.
    cases.append(case_from("performance-first", full, full[0]))
    cases.append(case_from("performance-last", full, full[-1]))
    cases.append(case_from("performance-middle", full, full[MAX_LENGTH // 2]))
    cases.append(case_from("performance-quarter", full, full[MAX_LENGTH // 4]))
    cases.append(case_from("performance-missing-below", full, LOW))
    cases.append(case_from("performance-missing-above", full, HIGH))
    cases.append(
        case_from(
            "performance-missing-between",
            full,
            absent_value(rng, full, full[0], full[-1]),
        )
    )
    dense = list(range(-MAX_LENGTH // 2 + 1, MAX_LENGTH // 2 + 1))
    cases.append(case_from("performance-consecutive-found", dense, dense[7777]))
    cases.append(
        case_from("performance-consecutive-missing-above", dense, dense[-1] + 1)
    )
    return {
        "version": SUITE_VERSION,
        "seed": SEED,
        "generator": "tools/build_binary_search_suite.py",
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
    parser = argparse.ArgumentParser(description="Build the Binary Search suite.")
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
