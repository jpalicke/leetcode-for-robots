# ABOUTME: Checks the committed LeetCode 704 package files without running any solution.
# ABOUTME: Recomputes every expected index with a dict lookup, not a halving search.

import json
import re
import subprocess
import sys
from typing import Any

from practice.classification import is_spoiler
from practice.package import load_package
from practice.paths import REPO_ROOT, default_package_dir
from practice.stubs import is_stub

PACKAGE = REPO_ROOT / "problems" / "leetcode-704"
MAX_LENGTH = 10**4
LOW, HIGH = -9999, 9999  # The page's bounds are strict: -10^4 < value < 10^4.
EM_DASH = chr(0x2014)
# Words that would name the technique; allowed only in the last hint level.
TECHNIQUE_PATTERN = re.compile(
    r"\b(binary|bisect|bisection|halve|halves|halving|half|middle|mid|midpoint"
    r"|logarithm|logarithmic|log)\b"
)


def cases() -> list[dict[str, Any]]:
    suite = json.loads((PACKAGE / "tests.json").read_text(encoding="utf-8"))
    found: list[dict[str, Any]] = suite["cases"]
    return found


def position_of(nums: list[int], target: int) -> int:
    """Oracle: look every value up in a dict built in one pass. Not a halving search."""
    where = {value: index for index, value in enumerate(nums)}
    return where.get(target, -1)


def test_the_package_is_found_by_default_without_a_flag() -> None:
    assert default_package_dir("leetcode", "704") == PACKAGE
    package = load_package(PACKAGE)
    assert (package.platform, package.problem_id) == ("leetcode", "704")
    assert package.function_name == "search"
    assert package.parameters == ("nums", "target")
    assert package.checker == "exact"
    assert package.allow_none is False


def test_the_starter_is_a_blank_typed_stub() -> None:
    source = (PACKAGE / "starter.py").read_text(encoding="utf-8")
    assert is_stub(source, "search", allow_none=False)
    assert "nums: list[int]" in source and "target: int" in source
    assert "-> int" in source
    assert source.startswith("# ABOUTME: ")


def test_every_case_obeys_the_published_constraints() -> None:
    for case in cases():
        nums, target = case["args"]
        assert 1 <= len(nums) <= MAX_LENGTH, case["id"]
        assert all(type(v) is int and LOW <= v <= HIGH for v in nums), case["id"]
        assert type(target) is int and LOW <= target <= HIGH, case["id"]
        assert all(a < b for a, b in zip(nums, nums[1:], strict=False)), case["id"]


def test_every_expected_index_is_an_integer_the_oracle_agrees_with() -> None:
    for case in cases():
        nums, target = case["args"]
        assert type(case["expected"]) is int, case["id"]
        assert case["expected"] == position_of(nums, target), case["id"]
        if case["expected"] != -1:
            assert nums[case["expected"]] == target, case["id"]


def test_the_suite_has_found_and_missing_targets_in_real_numbers() -> None:
    found = [c for c in cases() if c["expected"] != -1]
    missing = [c for c in cases() if c["expected"] == -1]
    assert len(found) >= 35
    assert len(missing) >= 25


def test_performance_cases_are_maximum_size() -> None:
    big = [case for case in cases() if len(case["args"][0]) == MAX_LENGTH]
    assert len(big) >= 5
    for case in big:
        assert case["id"].startswith("performance-")
    assert {case["expected"] == -1 for case in big} == {True, False}


def test_found_targets_cover_every_region_of_the_array() -> None:
    first = last = middle = 0
    for case in cases():
        nums, _ = case["args"]
        index = case["expected"]
        if index == 0 and len(nums) > 1:
            first += 1
        if index == len(nums) - 1 and len(nums) > 1:
            last += 1
        if len(nums) >= 3 and index == len(nums) // 2:
            middle += 1
    assert first >= 3 and last >= 3 and middle >= 3


def test_missing_targets_cover_below_between_and_above() -> None:
    below = between = above = 0
    for case in cases():
        nums, target = case["args"]
        if case["expected"] != -1:
            continue
        if target < nums[0]:
            below += 1
        elif target > nums[-1]:
            above += 1
        else:
            between += 1
    assert below >= 4 and between >= 6 and above >= 4


def test_the_suite_covers_the_named_risks() -> None:
    ids = {case["id"] for case in cases()}
    for needed in (
        "platform-example-1",
        "platform-example-2",
        "single-element-found",
        "single-element-missing-below",
        "single-element-missing-above",
        "two-elements-first",
        "two-elements-last",
        "two-elements-missing-between",
        "target-is-first",
        "target-is-last",
        "target-below-all",
        "target-above-all",
        "target-between-neighbours",
        "extreme-low-found",
        "extreme-high-found",
        "all-negative-found",
        "zero-found",
        "even-length-lower-middle",
        "even-length-upper-middle",
        "odd-length-exact-middle",
    ):
        assert needed in ids, needed
    assert any(i.startswith("generated-small-") for i in ids)
    assert any(i.startswith("generated-medium-") for i in ids)
    assert len(ids) == len(cases())


def test_the_platform_examples_have_the_answers_the_page_lists() -> None:
    by_id = {case["id"]: case for case in cases()}
    assert by_id["platform-example-1"]["args"] == [[-1, 0, 3, 5, 9, 12], 9]
    assert by_id["platform-example-1"]["expected"] == 4
    assert by_id["platform-example-2"]["args"] == [[-1, 0, 3, 5, 9, 12], 2]
    assert by_id["platform-example-2"]["expected"] == -1


def test_the_committed_suite_is_what_the_generator_builds() -> None:
    result = subprocess.run(
        [
            sys.executable,
            "-I",
            str(REPO_ROOT / "tools" / "build_binary_search_suite.py"),
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
    assert "https://leetcode.com/problems/binary-search/" in text
    assert "class Solution" in text  # Explains the wrapper difference.
    assert "-1" in text
    assert "Given an array of integers nums which is sorted" not in text
    assert "O(log n)" in text  # The requirement is stated...
    assert "does not check" in text  # ...with the honest limit of the local tests.


def test_notes_cover_the_required_approaches_and_pitfalls() -> None:
    text = (PACKAGE / "notes.md").read_text(encoding="utf-8").lower()
    for word in ("linear scan", "binary search", "o(log n)", "o(n)", "pitfalls"):
        assert word in text
    assert text.startswith("# binary search")
    assert "spoiler" in text.splitlines()[2].lower()


def test_package_text_files_have_no_em_dashes() -> None:
    for path in PACKAGE.rglob("*"):
        if path.is_file() and path.suffix in {".md", ".json", ".py"}:
            assert EM_DASH not in path.read_text(encoding="utf-8"), path.name


def test_the_readiness_record_matches_the_package() -> None:
    record = json.loads((PACKAGE / "readiness.json").read_text(encoding="utf-8"))
    assert (record["platform"], record["problem_id"]) == ("leetcode", "704")
    assert record["slug"] == "binary-search"
    assert record["verification"]["verified"]
    not_verified = " ".join(record["verification"]["not_verified"])
    assert "O(log n)" in not_verified  # The local tests cannot enforce it.
