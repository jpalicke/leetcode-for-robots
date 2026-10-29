# ABOUTME: Checks the committed LeetCode 121 package files without running any solution.
# ABOUTME: Recomputes every expected profit two ways, neither being the usual one pass.

import json
import re
import subprocess
import sys
from typing import Any

from practice.classification import is_spoiler
from practice.package import load_package
from practice.paths import REPO_ROOT, default_package_dir
from practice.stubs import is_stub

PACKAGE = REPO_ROOT / "problems" / "leetcode-121"
MAX_LENGTH = 10**5
MAX_PRICE = 10**4
EM_DASH = chr(0x2014)
# Words that would name the technique; allowed only in the last hint level.
TECHNIQUE_PATTERN = re.compile(
    r"\b(one pass|single pass|running|kadane|greedy|sliding|dynamic|dp|prefix|suffix"
    r"|min so far|minimum so far|lowest so far)\b"
)


def cases() -> list[dict[str, Any]]:
    suite = json.loads((PACKAGE / "tests.json").read_text(encoding="utf-8"))
    found: list[dict[str, Any]] = suite["cases"]
    return found


def best_profit(prices: list[int]) -> int:
    """Oracle: walk from the right keeping the highest price still ahead of each day."""
    best = 0
    highest_ahead = prices[-1]
    for price in reversed(prices[:-1]):
        best = max(best, highest_ahead - price)
        highest_ahead = max(highest_ahead, price)
    return best


def brute_force(prices: list[int]) -> int:
    """Second oracle for short lists: try every buy day and every later sell day."""
    return max(
        [0]
        + [
            prices[sell] - prices[buy]
            for buy in range(len(prices))
            for sell in range(buy + 1, len(prices))
        ]
    )


def test_the_package_is_found_by_default_without_a_flag() -> None:
    assert default_package_dir("leetcode", "121") == PACKAGE
    package = load_package(PACKAGE)
    assert (package.platform, package.problem_id) == ("leetcode", "121")
    assert package.function_name == "maxProfit"
    assert package.parameters == ("prices",)
    assert package.checker == "exact"
    assert package.allow_none is False


def test_the_starter_is_a_blank_typed_stub() -> None:
    source = (PACKAGE / "starter.py").read_text(encoding="utf-8")
    assert is_stub(source, "maxProfit", allow_none=False)
    assert "prices: list[int]" in source
    assert "-> int" in source
    assert source.startswith("# ABOUTME: ")


def test_every_case_obeys_the_published_constraints() -> None:
    for case in cases():
        (prices,) = case["args"]
        assert 1 <= len(prices) <= MAX_LENGTH, case["id"]
        assert all(type(p) is int and 0 <= p <= MAX_PRICE for p in prices), case["id"]


def test_every_expected_profit_is_an_integer_both_oracles_agree_with() -> None:
    for case in cases():
        (prices,) = case["args"]
        assert type(case["expected"]) is int, case["id"]
        assert case["expected"] == best_profit(prices), case["id"]
        if len(prices) <= 400:
            assert case["expected"] == brute_force(prices), case["id"]
        assert case["expected"] >= 0, case["id"]


def test_the_suite_has_profitable_and_unprofitable_cases_in_real_numbers() -> None:
    profits = [case["expected"] for case in cases()]
    assert sum(1 for p in profits if p > 0) >= 40
    assert sum(1 for p in profits if p == 0) >= 12


def test_performance_cases_are_maximum_size() -> None:
    big = [case for case in cases() if len(case["args"][0]) == MAX_LENGTH]
    assert len(big) >= 4
    for case in big:
        assert case["id"].startswith("performance-")
    assert {case["expected"] == 0 for case in big} == {True, False}


def test_the_suite_covers_the_named_risks() -> None:
    ids = {case["id"] for case in cases()}
    for needed in (
        "platform-example-1",
        "platform-example-2",
        "single-day",
        "two-days-rising",
        "two-days-falling",
        "two-days-equal",
        "all-equal",
        "strictly-increasing",
        "strictly-decreasing",
        "lowest-price-is-last",
        "lowest-price-is-first",
        "highest-price-is-first",
        "global-max-before-global-min",
        "best-pair-avoids-global-minimum",
        "best-pair-avoids-both-extremes",
        "best-profit-before-a-new-low",
        "sells-on-the-last-day",
        "buys-on-the-first-day",
        "zero-prices-allowed",
        "extreme-profit",
        "extreme-fall",
    ):
        assert needed in ids, needed
    assert any(i.startswith("generated-small-") for i in ids)
    assert any(i.startswith("generated-medium-") for i in ids)
    assert len(ids) == len(cases())


def test_the_trap_cases_really_trip_the_shortcuts_they_name() -> None:
    by_id = {case["id"]: case["args"][0] for case in cases()}
    trap = by_id["global-max-before-global-min"]
    assert trap.index(max(trap)) < trap.index(min(trap))
    assert max(trap) - min(trap) != best_profit(trap)  # max minus min is wrong here.
    trap = by_id["best-pair-avoids-both-extremes"]
    assert best_profit(trap) not in (max(trap) - min(trap), trap[-1] - trap[0])
    trap = by_id["best-profit-before-a-new-low"]
    assert trap.index(min(trap)) > trap.index(max(trap))
    assert best_profit(trap) > trap[-1] - min(trap)  # Resetting at a new low loses it.
    trap = by_id["highest-price-is-first"]
    assert trap[0] == max(trap) and best_profit(trap) < max(trap) - min(trap)


def test_the_platform_examples_have_the_answers_the_page_lists() -> None:
    by_id = {case["id"]: case for case in cases()}
    assert by_id["platform-example-1"]["args"] == [[7, 1, 5, 3, 6, 4]]
    assert by_id["platform-example-1"]["expected"] == 5
    assert by_id["platform-example-2"]["args"] == [[7, 6, 4, 3, 1]]
    assert by_id["platform-example-2"]["expected"] == 0


def test_the_committed_suite_is_what_the_generator_builds() -> None:
    result = subprocess.run(
        [
            sys.executable,
            "-I",
            str(REPO_ROOT / "tools" / "build_best_time_to_buy_and_sell_stock_suite.py"),
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
    assert "https://leetcode.com/problems/best-time-to-buy-and-sell-stock/" in text
    assert "class Solution" in text  # Explains the wrapper difference.
    assert "`0`" in text
    assert "You are given an array prices where" not in text


def test_notes_cover_the_required_approaches_and_pitfalls() -> None:
    text = (PACKAGE / "notes.md").read_text(encoding="utf-8").lower()
    for word in ("brute force", "lowest price", "o(n^2)", "o(n)", "pitfalls"):
        assert word in text
    assert text.startswith("# best time to buy and sell stock")
    assert "spoiler" in text.splitlines()[2].lower()


def test_package_text_files_have_no_em_dashes() -> None:
    for path in PACKAGE.rglob("*"):
        if path.is_file() and path.suffix in {".md", ".json", ".py"}:
            assert EM_DASH not in path.read_text(encoding="utf-8"), path.name


def test_the_readiness_record_matches_the_package() -> None:
    record = json.loads((PACKAGE / "readiness.json").read_text(encoding="utf-8"))
    assert (record["platform"], record["problem_id"]) == ("leetcode", "121")
    assert record["slug"] == "best-time-to-buy-and-sell-stock"
    assert record["verification"]["verified"]
    assert record["verification"]["not_verified"]
