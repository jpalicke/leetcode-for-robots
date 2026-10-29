# ABOUTME: Checks the committed LeetCode 20 package files without running any solution.
# ABOUTME: Recomputes every expected answer with two oracles that use no stack.

import json
import re
import subprocess
import sys
from typing import Any

from practice.classification import is_spoiler
from practice.package import load_package
from practice.paths import REPO_ROOT, default_package_dir
from practice.stubs import is_stub

PACKAGE = REPO_ROOT / "problems" / "leetcode-20"
MAX_LENGTH = 10**4
BRACKETS = set("()[]{}")
EM_DASH = chr(0x2014)
CLOSERS = {"(": ")", "[": "]", "{": "}"}
PAIR_PATTERN = re.compile(r"\(\)|\[\]|\{\}")
# Words that would name the technique; allowed only in the last hint level.
TECHNIQUE_PATTERN = re.compile(
    r"\b(stack|stacks|push|pushing|pop|popping|lifo|queue|hash|map|dict|dictionary"
    r"|counter|counting|last in|first out)\b"
)


def cases() -> list[dict[str, Any]]:
    suite = json.loads((PACKAGE / "tests.json").read_text(encoding="utf-8"))
    found: list[dict[str, Any]] = suite["cases"]
    return found


def reduces_to_nothing(text: str) -> bool:
    """Oracle 1: delete adjacent matching pairs until nothing more can be deleted."""
    while True:
        text, removed = PAIR_PATTERN.subn("", text)
        if not removed:
            return text == ""


def parses(text: str) -> bool:
    """Oracle 2: a grammar check. Sequence := (open Sequence close) Sequence | empty."""

    def sequence(position: int) -> int | None:
        while position < len(text) and text[position] in CLOSERS:
            inner = sequence(position + 1)
            if inner is None or inner >= len(text):
                return None
            if text[inner] != CLOSERS[text[position]]:
                return None
            position = inner + 1
        return position

    return sequence(0) == len(text)


def test_the_package_is_found_by_default_without_a_flag() -> None:
    assert default_package_dir("leetcode", "20") == PACKAGE
    package = load_package(PACKAGE)
    assert (package.platform, package.problem_id) == ("leetcode", "20")
    assert package.function_name == "isValid"
    assert package.parameters == ("s",)
    assert package.checker == "exact"
    assert package.allow_none is False


def test_the_starter_is_a_blank_typed_stub() -> None:
    source = (PACKAGE / "starter.py").read_text(encoding="utf-8")
    assert is_stub(source, "isValid", allow_none=False)
    assert "s: str" in source
    assert "-> bool" in source
    assert source.startswith("# ABOUTME: ")


def test_every_case_obeys_the_assumed_constraints() -> None:
    for case in cases():
        (text,) = case["args"]
        assert type(text) is str, case["id"]
        assert 1 <= len(text) <= MAX_LENGTH, case["id"]
        assert set(text) <= BRACKETS, case["id"]


def test_every_expected_answer_is_a_boolean_both_oracles_agree_with() -> None:
    for case in cases():
        (text,) = case["args"]
        assert type(case["expected"]) is bool, case["id"]
        assert case["expected"] is reduces_to_nothing(text), case["id"]
        if len(text) <= 400:
            assert case["expected"] is parses(text), case["id"]


def test_the_suite_has_both_answers_in_real_numbers() -> None:
    answers = [case["expected"] for case in cases()]
    assert answers.count(True) >= 25
    assert answers.count(False) >= 35


def test_performance_cases_are_maximum_size() -> None:
    big = [case for case in cases() if len(case["args"][0]) == MAX_LENGTH]
    assert len(big) >= 4
    for case in big:
        assert case["id"].startswith("performance-")
    assert {case["expected"] for case in big} == {True, False}


def test_the_suite_covers_the_named_risks() -> None:
    ids = {case["id"] for case in cases()}
    for needed in (
        "single-open",
        "single-close",
        "close-before-open",
        "nested-all-kinds",
        "crossing-pairs",
        "sequential-all-kinds",
        "leftover-opener",
        "extra-closer",
        "wrong-kind-closer",
        "equal-counts-wrong-order",
        "odd-length",
        "mirror-only-would-fail",
        "only-openers",
        "only-closers",
    ):
        assert needed in ids, needed
    assert any(i.startswith("generated-small-") for i in ids)
    assert any(i.startswith("generated-medium-") for i in ids)
    assert len(ids) == len(cases())


def test_the_trap_cases_really_trip_the_shortcuts_they_name() -> None:
    by_id = {case["id"]: case["args"][0] for case in cases()}
    crossing = by_id["crossing-pairs"]
    assert all(crossing.count(o) == crossing.count(c) for o, c in CLOSERS.items())
    assert reduces_to_nothing(crossing) is False
    sequential = by_id["sequential-all-kinds"]
    assert reduces_to_nothing(sequential) is True
    assert sequential != "".join(
        CLOSERS[c] for c in reversed(sequential[: len(sequential) // 2])
    )
    nested = by_id["nested-all-kinds"]
    assert reduces_to_nothing(nested) is True
    assert len(PAIR_PATTERN.sub("", nested)) > 0  # One pass of removal is not enough.


def test_the_committed_suite_is_what_the_generator_builds() -> None:
    result = subprocess.run(
        [
            sys.executable,
            "-I",
            str(REPO_ROOT / "tools" / "build_valid_parentheses_suite.py"),
            "--check",
        ],
        capture_output=True,
        text=True,
        check=False,
        timeout=120,
    )
    assert result.returncode == 0, result.stderr


def test_the_hint_ladder_is_gradual_and_classified() -> None:
    index = json.loads((PACKAGE / "hints" / "index.json").read_text(encoding="utf-8"))
    hints = index["hints"]
    assert [hint["level"] for hint in hints] == list(range(len(hints)))
    assert len(hints) >= 4
    for hint in hints:
        assert hint["content_class"] == "hint"
        assert hint["spoiler"] is is_spoiler(hint["content_class"])
        assert (PACKAGE / "hints" / hint["file"]).is_file()
    assert [hint["names_technique"] for hint in hints] == [False] * (len(hints) - 1) + [
        True
    ]


def test_early_hints_do_not_name_the_technique() -> None:
    index = json.loads((PACKAGE / "hints" / "index.json").read_text(encoding="utf-8"))
    for hint in index["hints"][:-1]:
        text = (PACKAGE / "hints" / hint["file"]).read_text(encoding="utf-8").lower()
        found = TECHNIQUE_PATTERN.search(text)
        assert found is None, f"{hint['file']} mentions {found and found.group(0)!r}"


def test_each_hint_stays_within_its_own_level() -> None:
    """Hint files do not point at later levels, so reading one reveals no other."""
    for number in range(4):
        text = (PACKAGE / "hints" / f"{number}.md").read_text(encoding="utf-8")
        mentioned = {int(n) for n in re.findall(r"[Hh]int (\d)", text)}
        assert mentioned <= {number}, f"hint {number} refers to {mentioned}"


def test_the_statement_is_original_and_links_the_source() -> None:
    text = (PACKAGE / "statement.md").read_text(encoding="utf-8")
    assert "https://leetcode.com/problems/valid-parentheses/" in text
    assert "class Solution" in text  # Explains the wrapper difference.
    assert "`True`" in text and "`False`" in text
    assert "Given a string s containing just the characters" not in text


def test_notes_cover_the_required_approaches_and_pitfalls() -> None:
    text = (PACKAGE / "notes.md").read_text(encoding="utf-8").lower()
    for word in ("stack", "repeated removal", "o(n)", "o(n^2)", "pitfalls"):
        assert word in text
    assert text.startswith("# valid parentheses")
    assert "spoiler" in text.splitlines()[2].lower()


def test_package_text_files_have_no_em_dashes() -> None:
    for path in PACKAGE.rglob("*"):
        if path.is_file() and path.suffix in {".md", ".json", ".py"}:
            assert EM_DASH not in path.read_text(encoding="utf-8"), path.name


def test_the_readiness_record_matches_the_package() -> None:
    record = json.loads((PACKAGE / "readiness.json").read_text(encoding="utf-8"))
    assert (record["platform"], record["problem_id"]) == ("leetcode", "20")
    assert record["slug"] == "valid-parentheses"
    assert record["verification"]["verified"]
    assert record["verification"]["not_verified"]
