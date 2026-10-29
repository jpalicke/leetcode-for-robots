# ABOUTME: Builds problems/leetcode-121/tests.json from hand-picked and seeded cases.
# ABOUTME: Lowest-price-so-far is the oracle here; the tests check it two other ways.

import argparse
import json
import random
import sys
from itertools import accumulate
from pathlib import Path
from typing import Any

SEED = 20261029
SUITE_VERSION = "leetcode-121-v1"
MAX_LENGTH = 10**5
MAX_PRICE = 10**4
REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT = REPO_ROOT / "problems" / "leetcode-121" / "tests.json"

# (id, prices). The answer is never written here; the oracle finds it.
HAND_CASES: tuple[tuple[str, list[int]], ...] = (
    # The two examples listed on the problem page.
    ("platform-example-1", [7, 1, 5, 3, 6, 4]),
    ("platform-example-2", [7, 6, 4, 3, 1]),
    # Written for this project.
    ("example-buy-then-sell", [2, 7, 1, 5]),
    ("example-only-falls", [5, 4, 3]),
    ("single-day", [5]),
    ("single-day-zero", [0]),
    ("two-days-rising", [1, 6]),
    ("two-days-falling", [6, 1]),
    ("two-days-equal", [4, 4]),
    ("all-equal", [3, 3, 3, 3]),
    ("strictly-increasing", [1, 2, 3, 4, 5]),
    ("strictly-decreasing", [5, 4, 3, 2, 1]),
    ("lowest-price-is-last", [3, 5, 1]),
    ("lowest-price-is-first", [1, 9, 5]),
    ("highest-price-is-first", [9, 1, 4]),
    ("highest-price-is-last", [4, 2, 3, 8]),
    ("global-max-before-global-min", [8, 10, 1, 4]),
    ("best-pair-avoids-global-minimum", [5, 100, 1, 50]),
    ("best-pair-avoids-both-extremes", [20, 6, 11, 1]),
    ("best-profit-before-a-new-low", [1, 9, 0, 3]),
    ("best-profit-before-a-new-low-and-no-recovery", [2, 8, 1, 1]),
    ("sells-on-the-last-day", [4, 2, 3, 9]),
    ("buys-on-the-first-day", [1, 3, 2, 9]),
    ("buys-after-the-first-day", [5, 2, 7]),
    ("multiple-equal-minima", [2, 2, 5, 2, 9]),
    ("tied-best-profits", [1, 5, 1, 5]),
    ("up-down-up", [3, 10, 2, 4, 8]),
    ("zero-prices-allowed", [0, 0, 5, 0]),
    ("zero-then-higher", [0, 3, 0, 2]),
    ("extreme-profit", [0, 10000]),
    ("extreme-fall", [10000, 0]),
    ("extreme-wiggle", [10000, 0, 10000, 0, 10000]),
    ("profit-of-one", [3, 4]),
    ("long-flat-then-jump", [7, 7, 7, 7, 7, 8]),
    ("long-flat-then-drop", [7, 7, 7, 7, 7, 6]),
    ("peak-in-the-middle", [1, 3, 7, 3, 1]),
    ("valley-in-the-middle", [7, 3, 1, 3, 7]),
)


def best_profit(prices: list[int]) -> int:
    """Oracle: the best of (price minus the lowest price seen before it), or zero."""
    lowest_before = accumulate(prices, min)
    return max(0, max(p - low for p, low in zip(prices, lowest_before, strict=True)))


def case_from(case_id: str, prices: list[int]) -> dict[str, Any]:
    if not (1 <= len(prices) <= MAX_LENGTH):
        raise ValueError(f"{case_id}: length {len(prices)} breaks the constraints")
    if any(not (0 <= p <= MAX_PRICE) for p in prices):
        raise ValueError(f"{case_id}: a price breaks the constraints")
    return {"id": case_id, "args": [prices], "expected": best_profit(prices)}


def uniform(rng: random.Random, length: int, high: int) -> list[int]:
    return [rng.randint(0, high) for _ in range(length)]


def walk(rng: random.Random, length: int, step: int) -> list[int]:
    """A random walk kept inside the allowed range, so runs of rises and falls occur."""
    price = rng.randint(0, MAX_PRICE)
    prices = []
    for _ in range(length):
        prices.append(price)
        price = min(MAX_PRICE, max(0, price + rng.randint(-step, step)))
    return prices


def descending(rng: random.Random, length: int, low: int, high: int) -> list[int]:
    return sorted((rng.randint(low, high) for _ in range(length)), reverse=True)


def build_suite() -> dict[str, Any]:
    rng = random.Random(SEED)
    cases = [case_from(*hand) for hand in HAND_CASES]
    for number in range(1, 31):
        cases.append(
            case_from(
                f"generated-small-{number:02d}", uniform(rng, rng.randint(1, 8), 9)
            )
        )
    for number in range(1, 13):
        length = rng.randint(50, 400)
        prices = (
            uniform(rng, length, MAX_PRICE) if number % 2 else walk(rng, length, 300)
        )
        cases.append(case_from(f"generated-medium-{number:02d}", prices))
    for number in range(1, 7):
        cases.append(
            case_from(
                f"generated-wide-{number:02d}",
                walk(rng, rng.randint(1000, 5000), 150),
            )
        )
    for number in range(1, 5):
        cases.append(
            case_from(
                f"generated-falling-{number:02d}",
                descending(rng, rng.randint(2, 300), 0, MAX_PRICE),
            )
        )
    # Maximum length. A quadratic answer has no early exit on these.
    cases.append(case_from("performance-random", uniform(rng, MAX_LENGTH, MAX_PRICE)))
    cases.append(
        case_from(
            "performance-non-increasing", descending(rng, MAX_LENGTH, 0, MAX_PRICE)
        )
    )
    cases.append(case_from("performance-all-equal", [5] * MAX_LENGTH))
    late = descending(rng, MAX_LENGTH - 2, 1000, MAX_PRICE) + [0, MAX_PRICE]
    cases.append(case_from("performance-only-profit-is-at-the-end", late))
    return {
        "version": SUITE_VERSION,
        "seed": SEED,
        "generator": "tools/build_best_time_to_buy_and_sell_stock_suite.py",
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
    parser = argparse.ArgumentParser(description="Build the Best Time to Buy suite.")
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
