# ABOUTME: Checks the committed ticket plan against the real catalog, topics and rules.
# ABOUTME: Every problem must be in exactly one ticket; lists must add no tickets.

import json
import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest

from practice.catalog import DEFAULT_CATALOG_PATH, load_catalog
from practice.lists import DEFAULT_LISTS_DIR, load_lists
from practice.paths import REPO_ROOT
from practice.topics import DEFAULT_TOPICS_PATH, load_topics

TOOL = REPO_ROOT / "tools" / "plan_catalog.py"
PLAN = REPO_ROOT / "catalog" / "ticket-plan.json"
RULES = REPO_ROOT / "catalog" / "class-rules.json"
STARTERS = {1: 20, 217: 21, 242: 22, 20: 23, 704: 24, 121: 25}


def tool(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-I", str(TOOL), *args],
        capture_output=True,
        text=True,
        check=False,
        timeout=300,
    )


@pytest.fixture(scope="module")
def plan() -> dict[str, Any]:
    loaded = json.loads(PLAN.read_text(encoding="utf-8"))
    assert isinstance(loaded, dict)
    return loaded


@pytest.fixture(scope="module")
def classes(plan: dict[str, Any]) -> list[dict[str, Any]]:
    found: list[dict[str, Any]] = plan["classes"]
    return found


def test_the_committed_plan_is_complete_current_and_free_of_drift() -> None:
    result = tool("check", "--strict")
    assert result.returncode == 0, result.stderr
    assert "4096 problems" in result.stdout and "exactly once" in result.stdout


def test_every_catalog_problem_is_in_exactly_one_ticket(
    classes: list[dict[str, Any]],
) -> None:
    catalog = load_catalog(DEFAULT_CATALOG_PATH)
    placed = [n for c in classes for n in c["entries"]]
    assert sorted(placed) == sorted(e.frontend_question_id for e in catalog.entries)
    assert len(placed) == len(set(placed)) == 4096
    assert all(c["removed"] == [] for c in classes)  # The snapshot lost nothing.


def test_no_ticket_holds_more_than_the_ticket_size(
    plan: dict[str, Any], classes: list[dict[str, Any]]
) -> None:
    assert plan["ticket_size"] == 100
    assert max(len(c["entries"]) for c in classes) <= 100


def test_the_six_starters_keep_their_existing_tickets(
    classes: list[dict[str, Any]],
) -> None:
    individual = {
        c["entries"][0]: c["issue"] for c in classes if c["kind"] == "individual"
    }
    assert individual == STARTERS
    for c in classes:
        if c["kind"] == "individual":
            assert len(c["entries"]) == 1 and c["id"] == f"problem-{c['entries'][0]}"


def test_blocked_tickets_say_why_and_pending_ones_do_not(
    classes: list[dict[str, Any]],
) -> None:
    for c in classes:
        if c["status"] == "blocked":
            assert c["reason"], c["id"]
        else:
            assert c["reason"] == "", c["id"]
        assert c["status"] in {"pending", "blocked", "in_progress"}


def test_every_ticket_has_its_own_issue_number(classes: list[dict[str, Any]]) -> None:
    numbers = [c["issue"] for c in classes]
    assert all(isinstance(n, int) for n in numbers)
    assert len(set(numbers)) == len(numbers)


def test_every_premium_problem_is_in_a_blocked_premium_ticket(
    classes: list[dict[str, Any]],
) -> None:
    catalog = load_catalog(DEFAULT_CATALOG_PATH)
    premium = {e.frontend_question_id for e in catalog.entries if e.paid_only}
    in_premium = {n for c in classes if c["rule"] == "premium" for n in c["entries"]}
    assert in_premium == premium - set(STARTERS)
    assert all(c["status"] == "blocked" for c in classes if c["rule"] == "premium")


def test_specialized_problems_are_blocked_whatever_their_topics(
    classes: list[dict[str, Any]],
) -> None:
    catalog = load_catalog(DEFAULT_CATALOG_PATH)
    topics = load_topics(DEFAULT_TOPICS_PATH, catalog)
    ticket_of = {n: c for c in classes for n in c["entries"]}
    for number, facts in topics.facts.items():
        if number in STARTERS:
            continue
        ticket = ticket_of[number]
        if {"database", "pandas", "shell", "concurrency", "javascript"} & set(
            facts.categories
        ):
            assert ticket["status"] == "blocked", number
        if {"design", "interactive"} & set(facts.topics):
            assert ticket["status"] == "blocked", number


def test_the_lists_add_no_tickets_and_every_list_problem_has_one(
    classes: list[dict[str, Any]],
) -> None:
    catalog = load_catalog(DEFAULT_CATALOG_PATH)
    listed = {
        p.frontend_question_id
        for item in load_lists(DEFAULT_LISTS_DIR, catalog)
        for p in item.problems
    }
    placed = {n for c in classes for n in c["entries"]}
    assert listed <= placed


def test_the_report_adds_up_and_matches_the_packages_on_disk() -> None:
    result = tool("report", "--json")
    assert result.returncode == 0, result.stderr
    report = json.loads(result.stdout)
    totals = report["totals"]
    assert report["problems"] == 4096 == sum(totals.values())
    assert report["exactly_once"] is True and report["removed"] == 0
    assert totals["ready"] == 6 and totals["in_progress"] == 0
    for item in report["lists"]:
        assert sum(item["counts"].values()) == item["size"], item["id"]
    ready = {c["id"] for c in report["classes"] if c["status"] == "ready"}
    assert ready == {f"problem-{n}" for n in STARTERS}


def test_every_ticket_body_can_be_rendered() -> None:
    for ticket in ("problem-1", "premium-01", "dp-hard-01", "uncategorised-01"):
        result = tool("render", ticket)
        assert result.returncode == 0, (ticket, result.stderr)
        assert result.stdout.startswith("# ")
        assert "Sub-issue of #1" in result.stdout


def test_a_rendered_ticket_names_every_problem_in_it(
    classes: list[dict[str, Any]],
) -> None:
    ticket = next(c for c in classes if c["id"] == "trees-easy-01")
    body = tool("render", "trees-easy-01").stdout
    assert body.count("- [ ] ") == len(ticket["entries"])


def test_the_rules_file_names_the_starters_with_their_issues() -> None:
    rules = json.loads(RULES.read_text(encoding="utf-8"))
    assert {r["problem"]: r["issue"] for r in rules["individual"]} == STARTERS


def test_the_plan_file_is_one_ticket_per_block_with_inline_problem_lists(
    plan: dict[str, Any],
) -> None:
    text = Path(PLAN).read_text(encoding="utf-8")
    assert text.endswith("}\n")
    assert '"entries": [' in text and text.count('"entries"') == len(plan["classes"])
    assert max(len(line) for line in text.splitlines()) < 700
