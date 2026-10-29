# ABOUTME: Checks the committed LeetCode 242 package files without running any solution.
# ABOUTME: Recomputes every expected answer with an independent letter-tally comparison.

import json
import re
import string
import subprocess
import sys
from collections import Counter
from typing import Any

from practice.classification import is_spoiler
from practice.package import load_package
from practice.paths import REPO_ROOT, default_package_dir
from practice.stubs import is_stub

PACKAGE = REPO_ROOT / "problems" / "leetcode-242"
MAX_LENGTH = 5 * 10**4
EM_DASH = chr(0x2014)
# Words that would name the technique; allowed only in the last hint level.
TECHNIQUE_PATTERN = re.compile(
    r"\b(hash|hashing|map|dict|dictionary|sort|sorted|sorting|counter|counting"
    r"|frequency|frequencies|histogram|tally|set|sets)\b"
)


def cases() -> list[dict[str, Any]]:
    suite = json.loads((PACKAGE / "tests.json").read_text(encoding="utf-8"))
    found: list[dict[str, Any]] = suite["cases"]
    return found


def is_anagram(s: str, t: str) -> bool:
    """Independent oracle: same letters with the same multiplicities."""
    return Counter(s) == Counter(t)


def test_the_package_is_found_by_default_without_a_flag() -> None:
    assert default_package_dir("leetcode", "242") == PACKAGE
    package = load_package(PACKAGE)
    assert (package.platform, package.problem_id) == ("leetcode", "242")
    assert package.function_name == "isAnagram"
    assert package.parameters == ("s", "t")
    assert package.checker == "exact"
    assert package.allow_none is False


def test_the_starter_is_a_blank_typed_stub() -> None:
    source = (PACKAGE / "starter.py").read_text(encoding="utf-8")
    assert is_stub(source, "isAnagram", allow_none=False)
    assert "s: str" in source and "t: str" in source
    assert "-> bool" in source
    assert source.startswith("# ABOUTME: ")


def test_every_case_obeys_the_assumed_constraints() -> None:
    for case in cases():
        s, t = case["args"]
        for text in (s, t):
            assert type(text) is str, case["id"]
            assert 1 <= len(text) <= MAX_LENGTH, case["id"]
            assert set(text) <= set(string.ascii_lowercase), case["id"]


def test_every_expected_answer_is_a_boolean_the_oracle_agrees_with() -> None:
    for case in cases():
        s, t = case["args"]
        assert type(case["expected"]) is bool, case["id"]
        assert case["expected"] is is_anagram(s, t), case["id"]


def test_the_suite_has_both_answers_in_real_numbers() -> None:
    answers = [case["expected"] for case in cases()]
    assert answers.count(True) >= 25
    assert answers.count(False) >= 25


def test_performance_cases_are_maximum_size() -> None:
    big = [case for case in cases() if len(case["args"][0]) == MAX_LENGTH]
    assert len(big) >= 3
    for case in big:
        assert case["id"].startswith("performance-")
        assert len(case["args"][1]) == MAX_LENGTH
    assert {case["expected"] for case in big} == {True, False}


def test_the_suite_covers_the_named_risks() -> None:
    ids = {case["id"] for case in cases()}
    for needed in (
        "platform-example-1",
        "platform-example-2",
        "single-letter-same",
        "single-letter-different",
        "identical-strings",
        "reversed-string",
        "different-lengths-prefix",
        "different-lengths-extra-letter",
        "same-letters-different-counts",
        "same-length-different-letters",
        "same-total-of-letter-codes",
        "differs-in-the-last-letter",
        "differs-in-the-first-letter",
        "all-one-letter",
        "full-alphabet-shuffled",
        "full-alphabet-one-letter-changed",
    ):
        assert needed in ids, needed
    assert any(i.startswith("generated-small-") for i in ids)
    assert any(i.startswith("generated-wide-") for i in ids)
    assert len(ids) == len(cases())


def test_the_same_total_of_letter_codes_case_really_has_equal_totals() -> None:
    by_id = {case["id"]: case for case in cases()}
    s, t = by_id["same-total-of-letter-codes"]["args"]
    assert sum(map(ord, s)) == sum(map(ord, t))
    assert is_anagram(s, t) is False


def test_the_platform_examples_have_the_answers_the_page_lists() -> None:
    by_id = {case["id"]: case for case in cases()}
    assert by_id["platform-example-1"]["args"] == ["anagram", "nagaram"]
    assert by_id["platform-example-1"]["expected"] is True
    assert by_id["platform-example-2"]["args"] == ["rat", "car"]
    assert by_id["platform-example-2"]["expected"] is False


def test_the_committed_suite_is_what_the_generator_builds() -> None:
    result = subprocess.run(
        [
            sys.executable,
            "-I",
            str(REPO_ROOT / "tools" / "build_valid_anagram_suite.py"),
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
    assert "https://leetcode.com/problems/valid-anagram/" in text
    assert "class Solution" in text  # Explains the wrapper difference.
    assert "`True`" in text and "`False`" in text
    assert "Given two strings s and t" not in text  # The platform's own wording.


def test_notes_cover_the_required_approaches_and_pitfalls() -> None:
    text = (PACKAGE / "notes.md").read_text(encoding="utf-8").lower()
    for word in ("sorting", "letter counts", "o(n log n)", "o(n)", "pitfalls"):
        assert word in text
    assert text.startswith("# valid anagram")
    assert "spoiler" in text.splitlines()[2].lower()


def test_package_text_files_have_no_em_dashes() -> None:
    for path in PACKAGE.rglob("*"):
        if path.is_file() and path.suffix in {".md", ".json", ".py"}:
            assert EM_DASH not in path.read_text(encoding="utf-8"), path.name


def test_the_readiness_record_matches_the_package() -> None:
    record = json.loads((PACKAGE / "readiness.json").read_text(encoding="utf-8"))
    assert (record["platform"], record["problem_id"]) == ("leetcode", "242")
    assert record["slug"] == "valid-anagram"
    assert record["verification"]["verified"]
    assert record["verification"]["not_verified"]
