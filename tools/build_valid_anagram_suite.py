# ABOUTME: Builds problems/leetcode-242/tests.json from hand-picked and seeded cases.
# ABOUTME: Comparing sorted letters is the oracle; the answer is never written by hand.

import argparse
import json
import random
import string
import sys
from pathlib import Path
from typing import Any

SEED = 20261029
SUITE_VERSION = "leetcode-242-v2"
MAX_LENGTH = 5 * 10**4  # Assumed from the published constraints.
ALPHABET = string.ascii_lowercase
REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT = REPO_ROOT / "problems" / "leetcode-242" / "tests.json"

# (id, s, t). The answer is never written here; the oracle finds it.
HAND_CASES: tuple[tuple[str, str, str], ...] = (
    # The two examples listed on the problem page, as the owner reported them.
    ("platform-example-1", "anagram", "nagaram"),
    ("platform-example-2", "rat", "car"),
    ("example-anagram", "listen", "silent"),
    ("example-different-letters", "stone", "stoke"),
    ("example-same-letters-different-counts", "aab", "abb"),
    ("single-letter-same", "q", "q"),
    ("single-letter-different", "q", "r"),
    ("identical-strings", "level", "level"),
    ("reversed-string", "stressed", "desserts"),
    ("different-lengths-prefix", "ab", "abc"),
    ("different-lengths-extra-letter", "abc", "abcc"),
    ("different-lengths-extra-letter-first", "bcd", "abcd"),
    ("same-letters-different-counts", "aabb", "abbb"),
    ("same-letter-set-more-of-one", "aaab", "abbb"),
    ("same-length-different-letters", "abcd", "abce"),
    ("same-total-of-letter-codes", "ad", "bc"),
    ("same-total-of-letter-codes-longer", "adz", "bcz"),
    ("differs-in-the-last-letter", "abcdefg", "abcdefh"),
    ("differs-in-the-first-letter", "zbcdefg", "abcdefg"),
    ("all-one-letter", "aaaaaa", "aaaaaa"),
    ("all-one-letter-versus-another", "aaaaaa", "bbbbbb"),
    ("one-extra-repeat", "aaaaab", "aaaabb"),
    ("two-pairs-swapped", "abba", "baab"),
    ("interleaved", "abcabc", "aabbcc"),
    ("end-letters-swapped", "zabcy", "yabcz"),
    ("letters-a-and-z-only", "azazaz", "zzzaaa"),
    ("full-alphabet-shuffled", ALPHABET, "mnbvcxzlkjhgfdsapoiuytrewq"),
    ("full-alphabet-one-letter-changed", ALPHABET, ALPHABET[:-1] + "a"),
    ("full-alphabet-versus-doubled", ALPHABET, ALPHABET + ALPHABET),
)


def is_anagram(s: str, t: str) -> bool:
    """Oracle: two strings are anagrams when their sorted letters are equal."""
    return sorted(s) == sorted(t)


def case_from(case_id: str, s: str, t: str) -> dict[str, Any]:
    for text in (s, t):
        if not (1 <= len(text) <= MAX_LENGTH):
            raise ValueError(f"{case_id}: length {len(text)} breaks the constraints")
        if not set(text) <= set(ALPHABET):
            raise ValueError(f"{case_id}: a character breaks the constraints")
    return {"id": case_id, "args": [s, t], "expected": is_anagram(s, t)}


def random_text(rng: random.Random, length: int, letters: str) -> str:
    return "".join(rng.choice(letters) for _ in range(length))


def shuffled(rng: random.Random, text: str) -> str:
    letters = list(text)
    rng.shuffle(letters)
    return "".join(letters)


def changed_letter(rng: random.Random, text: str, letters: str) -> str:
    """The same string with one position replaced by a different letter."""
    position = rng.randrange(len(text))
    replacement = rng.choice([c for c in letters if c != text[position]])
    return text[:position] + replacement + text[position + 1 :]


def pair(rng: random.Random, number: int, length: int, letters: str) -> tuple[str, str]:
    """Cycle through six shapes, half of them anagrams, so both answers stay common."""
    base = random_text(rng, length, letters)
    shape = number % 6
    if shape in (0, 2, 4):
        return base, shuffled(rng, base)
    if shape == 1:
        return base, shuffled(rng, changed_letter(rng, base, letters))
    if shape == 3:
        return base, shuffled(rng, base + rng.choice(letters))
    return base, random_text(rng, length, letters)


def build_suite() -> dict[str, Any]:
    rng = random.Random(SEED)
    cases = [case_from(*hand) for hand in HAND_CASES]
    for number in range(1, 25):
        length = rng.randint(1, 8)
        cases.append(
            case_from(
                f"generated-small-{number:02d}", *pair(rng, number, length, "abc")
            )
        )
    for number in range(1, 13):
        length = rng.randint(50, 400)
        cases.append(
            case_from(
                f"generated-medium-{number:02d}",
                *pair(rng, number, length, ALPHABET[:6]),
            )
        )
    for number in range(1, 13):
        length = rng.randint(20, 300)
        cases.append(
            case_from(
                f"generated-wide-{number:02d}", *pair(rng, number, length, ALPHABET)
            )
        )
    base = random_text(rng, MAX_LENGTH, ALPHABET)
    cases.append(case_from("performance-anagram", base, shuffled(rng, base)))
    near = shuffled(rng, changed_letter(rng, base, ALPHABET))
    cases.append(case_from("performance-one-letter-changed", base, near))
    cases.append(
        case_from("performance-all-one-letter", "a" * MAX_LENGTH, "a" * MAX_LENGTH)
    )
    return {
        "version": SUITE_VERSION,
        "seed": SEED,
        "generator": "tools/build_valid_anagram_suite.py",
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
    parser = argparse.ArgumentParser(description="Build the Valid Anagram suite.")
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
