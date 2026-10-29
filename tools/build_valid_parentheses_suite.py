# ABOUTME: Builds problems/leetcode-20/tests.json from hand-picked and seeded cases.
# ABOUTME: Repeated pair removal is the oracle; the answer is never written by hand.

import argparse
import json
import random
import re
import sys
from pathlib import Path
from typing import Any

SEED = 20261029
SUITE_VERSION = "leetcode-20-v1"
MAX_LENGTH = 10**4
BRACKETS = "()[]{}"
OPENERS = "([{"
CLOSER_OF = {"(": ")", "[": "]", "{": "}"}
PAIR_PATTERN = re.compile(r"\(\)|\[\]|\{\}")
REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT = REPO_ROOT / "problems" / "leetcode-20" / "tests.json"

# (id, s). The answer is never written here; the oracle finds it.
HAND_CASES: tuple[tuple[str, str], ...] = (
    # The five examples listed on the problem page.
    ("platform-example-1", "()"),
    ("platform-example-2", "()[]{}"),
    ("platform-example-3", "(]"),
    ("platform-example-4", "([])"),
    ("platform-example-5", "([)]"),
    # Written for this project.
    ("example-nested-braces", "[{}]"),
    ("example-braces-cross", "{[}]"),
    ("example-two-openers", "(("),
    ("single-open", "("),
    ("single-close", ")"),
    ("close-before-open", ")("),
    ("nested-all-kinds", "([{}])"),
    ("nested-all-kinds-reversed", "{[()]}"),
    ("crossing-pairs", "([)]{}"),
    ("sequential-all-kinds", "(){}[]"),
    ("sequential-and-nested", "{[]}()"),
    ("leftover-opener", "(()"),
    ("leftover-opener-after-pair", "()["),
    ("extra-closer", "())"),
    ("extra-closer-after-pair", "(){]"),
    ("wrong-kind-closer", "(}"),
    ("wrong-kind-closer-brace", "{)"),
    ("wrong-kind-closer-bracket", "[}"),
    ("wrong-kind-closer-inside", "({]})"),
    ("equal-counts-wrong-order", "))(("),
    ("equal-counts-per-kind-but-crossing", "[(])"),
    ("odd-length", "((("),
    ("odd-length-balanced-prefix", "(){}["),
    ("mirror-only-would-fail", "()()"),
    ("mirror-only-would-fail-mixed", "[](){}"),
    ("only-openers", "([{"),
    ("only-closers", ")]}"),
    ("deeply-nested-pair", "(((((())))))"),
    ("deep-then-one-too-many", "((((()))))" + ")"),
    ("deep-then-one-too-few", "(((((" + "))))"),
    ("repeat-same-kind", "()()()()"),
    ("braces-and-brackets-interleaved-wrong", "{[}{]}"),
    ("pair-wrapped-in-wrong-pair", "(()]"),
    ("closer-matches-an-earlier-opener", "([{}"),
    ("closer-skips-an-open-kind", "{(})"),
)


def is_valid(text: str) -> bool:
    """Oracle: delete adjacent matching pairs until none are left; valid if empty."""
    while True:
        text, removed = PAIR_PATTERN.subn("", text)
        if not removed:
            return text == ""


def case_from(case_id: str, text: str) -> dict[str, Any]:
    if not (1 <= len(text) <= MAX_LENGTH):
        raise ValueError(f"{case_id}: length {len(text)} breaks the constraints")
    if not set(text) <= set(BRACKETS):
        raise ValueError(f"{case_id}: a character breaks the constraints")
    return {"id": case_id, "args": [text], "expected": is_valid(text)}


def balanced(rng: random.Random, pairs: int, nesting: float) -> str:
    """A random balanced string with the given number of pairs.

    nesting is the chance of opening a new pair while some are still allowed, so a
    high value gives deep nests and a low one gives long runs of small pairs.
    """
    result: list[str] = []
    open_kinds: list[str] = []
    remaining = pairs
    while remaining or open_kinds:
        if remaining and (not open_kinds or rng.random() < nesting):
            kind = rng.choice(OPENERS)
            result.append(kind)
            open_kinds.append(kind)
            remaining -= 1
        else:
            result.append(CLOSER_OF[open_kinds.pop()])
    return "".join(result)


def damaged(rng: random.Random, text: str) -> str:
    """Break a string in one of several ways. The oracle still decides the answer."""
    letters = list(text)
    how = rng.randrange(6)
    spot = rng.randrange(len(letters))
    if how == 0 and len(letters) > 1:  # Drop one character.
        del letters[spot]
    elif how == 1:  # Replace one character with any bracket.
        letters[spot] = rng.choice(BRACKETS)
    elif how == 2:  # Turn a closer into a different closer.
        closers = [i for i, c in enumerate(letters) if c in ")]}"]
        if closers:
            letters[rng.choice(closers)] = rng.choice(")]}")
    elif how == 3:  # Swap two neighbours.
        if len(letters) > 1:
            other = spot - 1 if spot else 1
            letters[spot], letters[other] = letters[other], letters[spot]
    elif how == 4:  # Add a character.
        letters.insert(spot, rng.choice(BRACKETS))
    else:  # Reverse the string.
        letters.reverse()
    return "".join(letters) or rng.choice(BRACKETS)


def build_suite() -> dict[str, Any]:
    rng = random.Random(SEED)
    cases = [case_from(*hand) for hand in HAND_CASES]
    for number in range(1, 31):
        text = balanced(rng, rng.randint(1, 5), rng.choice((0.3, 0.6, 0.9)))
        if number % 2 == 0:
            text = damaged(rng, text)
        cases.append(case_from(f"generated-small-{number:02d}", text))
    for number in range(1, 17):
        text = balanced(rng, rng.randint(40, 200), rng.choice((0.3, 0.5, 0.8)))
        if number % 2 == 0:
            text = damaged(rng, text)
        cases.append(case_from(f"generated-medium-{number:02d}", text))
    half = MAX_LENGTH // 2
    cases.append(case_from("performance-deep-nest", _deep(rng, half)))
    cases.append(case_from("performance-long-sequence", _sequence(rng, half)))
    broken = list(_deep(rng, half))
    broken[half] = _other_closer(broken[half - 1])  # The first closer, wrong kind.
    cases.append(case_from("performance-deep-nest-one-wrong-closer", "".join(broken)))
    cases.append(case_from("performance-all-openers", "(" * MAX_LENGTH))
    cases.append(case_from("performance-all-closers", ")" * MAX_LENGTH))
    # Odd length: one opener is left over at the very end of a long valid run.
    cases.append(
        case_from("performance-leftover-opener", _sequence(rng, half - 1) + "(")
    )
    return {
        "version": SUITE_VERSION,
        "seed": SEED,
        "generator": "tools/build_valid_parentheses_suite.py",
        "cases": cases,
    }


def _deep(rng: random.Random, pairs: int) -> str:
    """pairs openers in a row, then the matching closers in reverse order."""
    openers = [rng.choice(OPENERS) for _ in range(pairs)]
    return "".join(openers) + "".join(CLOSER_OF[o] for o in reversed(openers))


def _sequence(rng: random.Random, pairs: int) -> str:
    """pairs small balanced groups one after another."""
    kinds = [rng.choice(OPENERS) for _ in range(pairs)]
    return "".join(kind + CLOSER_OF[kind] for kind in kinds)


def _other_closer(opener: str) -> str:
    """A closer of a different kind than the one that matches opener."""
    return next(c for c in ")]}" if c != CLOSER_OF[opener])


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
    parser = argparse.ArgumentParser(description="Build the Valid Parentheses suite.")
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
