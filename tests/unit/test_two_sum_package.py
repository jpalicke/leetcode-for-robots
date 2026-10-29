# ABOUTME: Checks the committed LeetCode 1 package files without running any solution.
# ABOUTME: Recomputes every expected answer with an independent brute-force search.

import json
import re
import subprocess
import sys
from typing import Any

from practice.classification import is_spoiler
from practice.package import load_package
from practice.paths import REPO_ROOT, default_package_dir
from practice.stubs import is_stub

PACKAGE = REPO_ROOT / "problems" / "leetcode-1"
LIMIT = 10**9
EM_DASH = chr(0x2014)
# Words that would name the technique; allowed only in the last hint level.
TECHNIQUE_WORDS = ("hash", "dictionary", "dict", "two pointer", "sort", "map")


def cases() -> list[dict[str, Any]]:
    suite = json.loads((PACKAGE / "tests.json").read_text(encoding="utf-8"))
    found: list[dict[str, Any]] = suite["cases"]
    return found


def pairs(nums: list[int], target: int) -> list[tuple[int, int]]:
    return [
        (i, j)
        for i in range(len(nums))
        for j in range(i + 1, len(nums))
        if nums[i] + nums[j] == target
    ]


def test_the_package_is_found_by_default_without_a_flag() -> None:
    assert default_package_dir("leetcode", "1") == PACKAGE
    package = load_package(PACKAGE)
    assert (package.platform, package.problem_id) == ("leetcode", "1")
    assert package.function_name == "twoSum"
    assert package.parameters == ("nums", "target")
    assert package.checker == "indices_sum_to_target"
    assert package.allow_none is False


def test_the_starter_is_a_blank_typed_stub() -> None:
    source = (PACKAGE / "starter.py").read_text(encoding="utf-8")
    assert is_stub(source, "twoSum", allow_none=False)
    assert "list[int]" in source
    assert source.startswith("# ABOUTME: ")


def test_every_case_obeys_the_published_constraints() -> None:
    for case in cases():
        nums, target = case["args"]
        assert 2 <= len(nums) <= 10_000, case["id"]
        assert all(-LIMIT <= value <= LIMIT for value in nums), case["id"]
        assert -LIMIT <= target <= LIMIT, case["id"]


def test_every_small_case_has_exactly_one_pair_and_the_expected_one() -> None:
    checked = 0
    for case in cases():
        nums, target = case["args"]
        if len(nums) > 400:
            continue
        found = pairs(nums, target)
        assert found == [tuple(case["expected"])], case["id"]
        checked += 1
    assert checked >= 60


def test_performance_cases_are_maximum_size_with_one_pair() -> None:
    big = [case for case in cases() if len(case["args"][0]) == 10_000]
    assert len(big) >= 2
    for case in big:
        nums, target = case["args"]
        assert case["id"].startswith("performance-")
        counts: dict[int, int] = {}
        for value in nums:
            counts[value] = counts.get(value, 0) + 1
        total = sum(
            counts[v] * counts.get(target - v, 0)
            for v in counts
            if v < target - v or (v == target - v and counts[v] > 1)
        )
        assert total == 1, case["id"]
        i, j = case["expected"]
        assert nums[i] + nums[j] == target


def test_the_suite_covers_the_named_risks() -> None:
    ids = {case["id"] for case in cases()}
    for needed in (
        "example-ascending",
        "duplicate-pair-only",
        "half-of-target-appears-once",
        "all-negative",
        "zero-target",
        "extreme-values-cancel",
        "pair-at-the-end",
        "minimum-length",
    ):
        assert needed in ids
    assert any(i.startswith("generated-small-") for i in ids)
    assert any(i.startswith("generated-wide-") for i in ids)
    assert len(ids) == len(cases())


def test_the_committed_suite_is_what_the_generator_builds() -> None:
    result = subprocess.run(
        [sys.executable, "-I", str(REPO_ROOT / "tools" / "build_two_sum_suite.py")]
        + ["--check"],
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
        for word in TECHNIQUE_WORDS:
            assert word not in text, f"{hint['file']} mentions {word!r}"


def test_each_hint_stays_within_its_own_level() -> None:
    """Hint files do not point at later levels, so reading one reveals no other."""
    for number in range(4):
        text = (PACKAGE / "hints" / f"{number}.md").read_text(encoding="utf-8")
        mentioned = {int(n) for n in re.findall(r"[Hh]int (\d)", text)}
        assert mentioned <= {number}, f"hint {number} refers to {mentioned}"


def test_the_statement_is_original_and_links_the_source() -> None:
    text = (PACKAGE / "statement.md").read_text(encoding="utf-8")
    assert "https://leetcode.com/problems/two-sum/" in text
    assert "class Solution" in text  # Explains the wrapper difference.
    assert "Return indices" in text
    assert "You may assume that each input would have exactly one solution" not in text


def test_notes_cover_the_required_approaches_and_pitfalls() -> None:
    text = (PACKAGE / "notes.md").read_text(encoding="utf-8").lower()
    for word in ("brute force", "hash map", "two pointers", "o(n^2)", "pitfalls"):
        assert word in text
    assert text.startswith("# two sum")
    assert "spoiler" in text.splitlines()[2].lower()


def test_package_text_files_have_no_em_dashes() -> None:
    for path in PACKAGE.rglob("*"):
        if path.is_file() and path.suffix in {".md", ".json", ".py"}:
            assert EM_DASH not in path.read_text(encoding="utf-8"), path.name


def test_the_readiness_record_matches_the_package() -> None:
    record = json.loads((PACKAGE / "readiness.json").read_text(encoding="utf-8"))
    assert (record["platform"], record["problem_id"]) == ("leetcode", "1")
    assert record["verification"]["verified"]
    assert record["verification"]["not_verified"]
    assert record["blockers"] == []
