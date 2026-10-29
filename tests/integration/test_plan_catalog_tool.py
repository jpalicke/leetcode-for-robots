# ABOUTME: Runs tools/plan_catalog.py on small invented catalogs, as a real process.
# ABOUTME: Each problem must land in exactly one ticket; re-planning must keep work.

import json
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest

from practice.paths import REPO_ROOT

TOOL = REPO_ROOT / "tools" / "plan_catalog.py"

# (id, title, slug, difficulty, premium, categories, topics)
ROWS: list[tuple[int, str, str, str, bool, list[str], list[str]]] = [
    (1, "Two Sum", "two-sum", "easy", False, ["algorithms"], ["array", "hash-table"]),
    (2, "Problem 2", "problem-2", "easy", False, ["algorithms"], ["array"]),
    (3, "Problem 3", "problem-3", "medium", False, ["algorithms"], ["array"]),
    (4, "Problem 4", "problem-4", "easy", True, ["algorithms"], ["array"]),
    (
        5,
        "Problem 5",
        "problem-5",
        "medium",
        False,
        ["database", "pandas"],
        ["database"],
    ),
    (6, "Problem 6", "problem-6", "hard", False, ["algorithms"], ["design", "array"]),
    (7, "Problem 7", "problem-7", "hard", False, ["algorithms"], ["interactive"]),
    (
        8,
        "Problem 8",
        "problem-8",
        "hard",
        False,
        ["algorithms"],
        ["dynamic-programming"],
    ),
    (
        9,
        "Problem 9",
        "problem-9",
        "hard",
        False,
        ["algorithms"],
        ["dynamic-programming"],
    ),
    (10, "Problem 10", "problem-10", "easy", False, ["algorithms"], []),
    (11, "Problem 11", "problem-11", "easy", False, ["algorithms"], ["string"]),
    (12, "Problem 12", "problem-12", "medium", False, ["algorithms"], ["hash-table"]),
    (13, "Problem 13", "problem-13", "easy", False, ["algorithms"], ["array"]),
    (14, "Problem 14", "problem-14", "easy", False, ["algorithms"], ["array"]),
]
RULES: dict[str, Any] = {
    "schema_version": 1,
    "ticket_size": 2,
    "individual": [{"problem": 1, "issue": 20}],
    "specialized": [
        {
            "id": "premium",
            "title": "premium problems",
            "reason": "Premium problems cannot be read without a subscription.",
            "match": {"premium": True},
        },
        {
            "id": "sql",
            "title": "SQL problems",
            "reason": "SQL needs a database runner.",
            "match": {"categories": ["database"]},
        },
        {
            "id": "interactive",
            "title": "interactive problems",
            "reason": "Interactive problems need an interactor.",
            "match": {"topics": ["interactive"]},
        },
        {
            "id": "design",
            "title": "stateful design problems",
            "reason": "Design problems need a stateful adapter.",
            "match": {"topics": ["design"]},
        },
    ],
    "ignored_tags": ["database", "design", "interactive"],
    "ignored_tags_note": "Handled by a specialized rule.",
    "concepts": [
        {"id": "dp", "tags": ["dynamic-programming"]},
        {"id": "lookup", "tags": ["hash-table"]},
        {"id": "strings", "tags": ["string"]},
        {"id": "arrays", "tags": ["array"]},
    ],
    "fallback": {
        "id": "uncategorised",
        "title": "problems with no topic tags",
        "note": "LeetCode lists no topic tags for these problems.",
        "split_by_difficulty": False,
    },
}


def catalog_json(rows: list[Any]) -> dict[str, Any]:
    return {
        "platform": "leetcode",
        "source_url": "https://leetcode.com/api/problems/all/",
        "fetched_on": "2026-10-28",
        "entries": [
            {
                "platform": "leetcode",
                "frontend_question_id": number,
                "question_id": number,
                "title": title,
                "slug": slug,
                "difficulty": difficulty,
                "paid_only": premium,
            }
            for number, title, slug, difficulty, premium, _, _ in rows
        ],
    }


def topics_json(rows: list[Any]) -> dict[str, Any]:
    return {
        "schema_version": 1,
        "platform": "leetcode",
        "source_url": "https://leetcode.com/graphql",
        "fetched_on": "2026-10-29",
        "note": "Category and topic tag slugs only; no problem text.",
        "entries": [
            {"id": row[0], "categories": sorted(row[5]), "topics": sorted(row[6])}
            for row in rows
        ],
    }


class Workspace:
    def __init__(self, root: Path) -> None:
        self.root = root
        self.catalog = root / "leetcode.json"
        self.topics = root / "topics.json"
        self.rules = root / "rules.json"
        self.plan = root / "ticket-plan.json"
        self.curriculum = root / "core.json"
        self.lists = root / "lists"
        self.problems = root / "problems"
        self.lists.mkdir()
        self.problems.mkdir()
        shutil.copyfile(REPO_ROOT / "curriculum" / "core.json", self.curriculum)
        self.write(ROWS, RULES)

    def write(self, rows: list[Any], rules: dict[str, Any]) -> None:
        self.catalog.write_text(json.dumps(catalog_json(rows)), encoding="utf-8")
        self.topics.write_text(json.dumps(topics_json(rows)), encoding="utf-8")
        self.rules.write_text(json.dumps(rules), encoding="utf-8")

    def run(
        self, *args: str, references: Path | None = None
    ) -> subprocess.CompletedProcess[str]:
        command = [
            sys.executable,
            "-I",
            str(TOOL),
            "--catalog",
            str(self.catalog),
            "--topics",
            str(self.topics),
            "--rules",
            str(self.rules),
            "--curriculum",
            str(self.curriculum),
            "--plan",
            str(self.plan),
            "--lists-dir",
            str(self.lists),
            "--problems-dir",
            str(self.problems),
            "--references",
            str(references or REPO_ROOT / "references"),
            *args,
        ]
        return subprocess.run(
            command, capture_output=True, text=True, check=False, timeout=120
        )

    def plan_data(self) -> dict[str, Any]:
        loaded = json.loads(self.plan.read_text(encoding="utf-8"))
        assert isinstance(loaded, dict)
        return loaded

    def classes(self) -> dict[str, dict[str, Any]]:
        return {c["id"]: c for c in self.plan_data()["classes"]}

    def class_of(self, number: int) -> str:
        for item in self.plan_data()["classes"]:
            if number in item["entries"]:
                return str(item["id"])
        raise AssertionError(f"problem {number} is in no class")


@pytest.fixture
def work(tmp_path: Path) -> Workspace:
    return Workspace(tmp_path)


def test_every_problem_lands_in_exactly_one_ticket(work: Workspace) -> None:
    result = work.run("plan")
    assert result.returncode == 0, result.stderr
    placed = [n for c in work.plan_data()["classes"] for n in c["entries"]]
    assert sorted(placed) == [row[0] for row in ROWS]
    assert len(placed) == len(set(placed))


def test_rules_decide_the_class_in_order(work: Workspace) -> None:
    assert work.run("plan").returncode == 0
    assert work.class_of(1) == "problem-1"  # A starter has its own ticket.
    assert work.class_of(4).startswith("premium-")  # Premium wins over its topics.
    assert work.class_of(5).startswith("sql-")  # A category beats a topic.
    assert work.class_of(6).startswith("design-")  # A specialized tag beats arrays.
    assert work.class_of(7).startswith("interactive-")
    assert work.class_of(8) == work.class_of(9)
    assert work.class_of(8).startswith("dp-hard-")
    assert work.class_of(10).startswith("uncategorised-")
    assert work.class_of(11).startswith("strings-easy-")
    assert work.class_of(12).startswith("lookup-medium-")
    assert work.class_of(2).startswith("arrays-easy-")


def test_the_most_advanced_concept_a_problem_needs_wins(work: Workspace) -> None:
    rows = [
        *ROWS,
        (
            15,
            "Problem 15",
            "problem-15",
            "easy",
            False,
            ["algorithms"],
            ["array", "string"],
        ),
    ]
    work.write(rows, RULES)
    assert work.run("plan").returncode == 0
    assert work.class_of(15).startswith("strings-easy-")  # Strings come after arrays.


def test_a_ticket_never_holds_more_than_the_ticket_size_and_is_balanced(
    work: Workspace,
) -> None:
    assert work.run("plan").returncode == 0
    arrays = [
        c for c in work.plan_data()["classes"] if c["id"].startswith("arrays-easy-")
    ]
    assert [len(c["entries"]) for c in arrays] == [2, 1]  # 2, 13, 14 at size 2.
    assert [c["entries"] for c in arrays] == [[2, 13], [14]]
    for item in work.plan_data()["classes"]:
        assert len(item["entries"]) <= 2


def test_blocked_and_pending_classes_carry_a_status_and_a_reason(
    work: Workspace,
) -> None:
    assert work.run("plan").returncode == 0
    classes = work.classes()
    premium = next(c for c in classes.values() if c["rule"] == "premium")
    assert premium["status"] == "blocked"
    assert "subscription" in premium["reason"]
    arrays = classes["arrays-easy-01"]
    assert arrays["status"] == "pending" and arrays["reason"] == ""
    assert classes["problem-1"]["issue"] == 20
    assert classes["problem-1"]["kind"] == "individual"
    assert classes["arrays-easy-01"]["issue"] is None


def test_titles_say_what_the_ticket_is(work: Workspace) -> None:
    assert work.run("plan").returncode == 0
    classes = work.classes()
    assert classes["problem-1"]["title"] == "Prepare LeetCode 1: Two Sum (Python)"
    assert (
        classes["arrays-easy-01"]["title"] == "Prepare arrays problems, easy (1 of 2)"
    )
    assert (
        classes["arrays-easy-02"]["title"] == "Prepare arrays problems, easy (2 of 2)"
    )
    assert (
        classes["dp-hard-01"]["title"] == "Prepare dynamic programming problems, hard"
    )
    assert classes["premium-01"]["title"] == "Track premium problems"
    assert classes["uncategorised-01"]["title"] == "Prepare problems with no topic tags"


def test_planning_twice_gives_a_byte_identical_file(work: Workspace) -> None:
    assert work.run("plan").returncode == 0
    first = work.plan.read_bytes()
    assert work.run("plan").returncode == 0
    assert work.plan.read_bytes() == first


def test_check_passes_on_a_fresh_plan(work: Workspace) -> None:
    assert work.run("plan").returncode == 0
    result = work.run("check")
    assert result.returncode == 0, result.stderr
    assert "14 problems" in result.stdout and "exactly once" in result.stdout


def test_an_unmapped_topic_tag_stops_the_plan_and_names_the_tag(
    work: Workspace,
) -> None:
    rows = [
        *ROWS[:-1],
        (14, "Problem 14", "problem-14", "easy", False, ["algorithms"], ["sorcery"]),
    ]
    work.write(rows, RULES)
    result = work.run("plan")
    assert result.returncode == 1
    assert (
        "sorcery" in result.stderr
        and "class-rules" in result.stderr
        or "rules" in result.stderr
    )
    assert not work.plan.exists()


def test_a_tag_in_two_concepts_is_a_rules_error(work: Workspace) -> None:
    rules = json.loads(json.dumps(RULES))
    rules["concepts"][3]["tags"].append("string")
    work.write(ROWS, rules)
    result = work.run("plan")
    assert result.returncode == 1
    assert "string" in result.stderr and "more than one" in result.stderr
    assert not work.plan.exists()


def test_a_concept_the_curriculum_does_not_know_is_a_rules_error(
    work: Workspace,
) -> None:
    rules = json.loads(json.dumps(RULES))
    rules["concepts"][0]["id"] = "quantum"
    work.write(ROWS, rules)
    result = work.run("plan")
    assert result.returncode == 1
    assert "quantum" in result.stderr
    assert not work.plan.exists()


def test_topics_that_miss_a_problem_stop_the_plan(work: Workspace) -> None:
    data = json.loads(work.topics.read_text(encoding="utf-8"))
    data["entries"] = [e for e in data["entries"] if e["id"] != 9]
    work.topics.write_text(json.dumps(data), encoding="utf-8")
    result = work.run("plan")
    assert result.returncode == 1
    assert "problem 9" in result.stderr
    assert not work.plan.exists()


def test_new_problems_join_existing_tickets_without_moving_old_ones(
    work: Workspace,
) -> None:
    assert work.run("plan").returncode == 0
    before = {n: work.class_of(n) for n in range(1, 15)}
    added = [
        (15, "Problem 15", "problem-15", "easy", False, ["algorithms"], ["array"]),
        (16, "Problem 16", "problem-16", "easy", False, ["algorithms"], ["array"]),
        (17, "Problem 17", "problem-17", "easy", False, ["algorithms"], ["array"]),
    ]
    work.write([*ROWS, *added], RULES)
    result = work.run("plan")
    assert result.returncode == 0, result.stderr
    assert {n: work.class_of(n) for n in range(1, 15)} == before  # Nothing moved.
    assert work.class_of(15) == "arrays-easy-02"  # The ticket with room.
    assert work.class_of(16) == "arrays-easy-03"  # A new ticket when it is full.
    assert work.class_of(17) == "arrays-easy-03"
    assert work.run("check").returncode == 0


def test_a_problem_that_leaves_the_catalog_is_kept_and_flagged_never_dropped(
    work: Workspace,
) -> None:
    assert work.run("plan").returncode == 0
    work.write([row for row in ROWS if row[0] != 12], RULES)
    result = work.run("plan")
    assert result.returncode == 0, result.stderr
    holder = work.classes()["lookup-medium-01"]
    assert holder["entries"] == [] and holder["removed"] == [12]
    assert "12" in result.stdout and "removed" in result.stdout.lower()
    report = work.run("report")
    assert "removed" in report.stdout.lower()
    assert work.run("check").returncode == 0


def test_issue_numbers_and_progress_survive_planning_again(work: Workspace) -> None:
    assert work.run("plan").returncode == 0
    data = work.plan_data()
    for item in data["classes"]:
        if item["id"] == "arrays-easy-01":
            item["issue"] = 77
            item["status"] = "in_progress"
        if item["id"] == "premium-01":
            item["issue"] = 78
    work.plan.write_text(json.dumps(data), encoding="utf-8")
    assert work.run("plan").returncode == 0
    classes = work.classes()
    assert classes["arrays-easy-01"]["issue"] == 77
    assert classes["arrays-easy-01"]["status"] == "in_progress"
    assert classes["premium-01"]["issue"] == 78
    assert classes["premium-01"]["status"] == "blocked"  # Rules own blocked.


def test_a_rule_change_does_not_move_problems_but_check_reports_the_drift(
    work: Workspace,
) -> None:
    assert work.run("plan").returncode == 0
    rules = json.loads(json.dumps(RULES))
    rules["concepts"][0]["tags"].append("string")  # Strings now count as dp.
    rules["concepts"][2]["tags"].remove("string")
    rules["concepts"][2]["tags"].append("never-used")
    work.write(ROWS, rules)
    assert work.run("plan").returncode == 0
    assert work.class_of(11).startswith("strings-easy-")  # Kept where it was.
    result = work.run("check")
    assert result.returncode == 0
    assert "drift" in result.stdout.lower() and "11" in result.stdout
    strict = work.run("check", "--strict")
    assert strict.returncode == 1
    assert "drift" in strict.stderr.lower()


def test_rebuild_applies_the_rules_but_keeps_issue_numbers(work: Workspace) -> None:
    assert work.run("plan").returncode == 0
    data = work.plan_data()
    for item in data["classes"]:
        if item["id"] == "dp-hard-01":
            item["issue"] = 91
    work.plan.write_text(json.dumps(data), encoding="utf-8")
    rules = json.loads(json.dumps(RULES))
    rules["concepts"][0]["tags"].append("string")
    rules["concepts"][2]["tags"].remove("string")
    rules["concepts"][2]["tags"].append("never-used")
    work.write(ROWS, rules)
    assert work.run("plan", "--rebuild").returncode == 0
    assert work.class_of(11).startswith("dp-easy-")  # Moved by the new rule.
    assert work.classes()["dp-hard-01"]["issue"] == 91
    assert work.run("check", "--strict").returncode == 0


def test_check_names_a_problem_that_is_in_no_ticket(work: Workspace) -> None:
    assert work.run("plan").returncode == 0
    data = work.plan_data()
    data["classes"][1]["entries"] = []
    data["classes"][1]["removed"] = []
    lost = [c for c in data["classes"]]
    work.plan.write_text(json.dumps({**data, "classes": lost}), encoding="utf-8")
    result = work.run("check")
    assert result.returncode == 1
    assert "in no ticket" in result.stderr


def test_check_names_a_problem_that_is_in_two_tickets(work: Workspace) -> None:
    assert work.run("plan").returncode == 0
    data = work.plan_data()
    data["classes"][1]["entries"].append(data["classes"][2]["entries"][0])
    work.plan.write_text(json.dumps(data), encoding="utf-8")
    result = work.run("check")
    assert result.returncode == 1
    assert "more than one ticket" in result.stderr


def test_check_refuses_an_oversized_ticket(work: Workspace) -> None:
    assert work.run("plan").returncode == 0
    data = work.plan_data()
    data["classes"][1]["entries"] = [*data["classes"][1]["entries"], 90, 91, 92]
    work.plan.write_text(json.dumps(data), encoding="utf-8")
    result = work.run("check")
    assert result.returncode == 1


def test_check_without_a_plan_says_so(work: Workspace) -> None:
    result = work.run("check")
    assert result.returncode == 1
    assert "plan" in result.stderr.lower()


def test_the_report_counts_every_problem_once_by_status(work: Workspace) -> None:
    assert work.run("plan").returncode == 0
    result = work.run("report", "--json")
    assert result.returncode == 0, result.stderr
    report = json.loads(result.stdout)
    totals = report["totals"]
    assert sum(totals.values()) == 14 == report["problems"]
    assert totals["ready"] == 0
    assert totals["blocked"] == 4  # Premium, SQL, design and interactive.
    assert totals["in_progress"] == 0
    assert totals["pending"] == 10
    assert report["exactly_once"] is True
    assert report["removed"] == 0


def test_in_progress_tickets_are_counted_apart_from_pending(work: Workspace) -> None:
    assert work.run("plan").returncode == 0
    data = work.plan_data()
    for item in data["classes"]:
        if item["id"] == "arrays-easy-01":
            item["status"] = "in_progress"
    work.plan.write_text(json.dumps(data), encoding="utf-8")
    totals = json.loads(work.run("report", "--json").stdout)["totals"]
    assert totals["in_progress"] == 2 and totals["pending"] == 8


def test_a_ready_package_makes_its_problem_ready_even_inside_a_class(
    work: Workspace,
) -> None:
    shutil.copytree(REPO_ROOT / "problems" / "leetcode-1", work.problems / "leetcode-1")
    assert work.run("plan").returncode == 0
    report = json.loads(work.run("report", "--json").stdout)
    assert report["totals"]["ready"] == 1
    assert report["totals"]["pending"] == 9  # 14 less 1 ready and 4 blocked.
    by_class = {c["id"]: c for c in report["classes"]}
    assert by_class["problem-1"]["counts"]["ready"] == 1


def test_a_ticket_whose_problems_are_all_ready_is_shown_as_ready(
    work: Workspace,
) -> None:
    shutil.copytree(REPO_ROOT / "problems" / "leetcode-1", work.problems / "leetcode-1")
    assert work.run("plan").returncode == 0
    report = json.loads(work.run("report", "--json").stdout)
    by_class = {c["id"]: c for c in report["classes"]}
    assert by_class["problem-1"]["status"] == "ready"
    assert by_class["arrays-easy-01"]["status"] == "pending"  # Nothing ready in it.
    assert by_class["premium-01"]["status"] == "blocked"
    assert (
        work.plan_data()["classes"][0]["status"] == "pending"
    )  # The plan is unchanged.
    assert "ready  " in work.run("report").stdout.split("problem-1")[1].splitlines()[0]


def test_the_report_shows_each_class_with_its_counts(work: Workspace) -> None:
    assert work.run("plan").returncode == 0
    text = work.run("report").stdout
    assert "14 problems" in text and "exactly once" in text
    for line in ("premium-01", "sql-01", "arrays-easy-01", "uncategorised-01"):
        assert line in text


def test_the_report_counts_each_list_by_status(work: Workspace) -> None:
    (work.lists / "tiny.json").write_text(
        json.dumps(
            {
                "schema_version": 1,
                "id": "tiny",
                "name": "Tiny",
                "platform": "leetcode",
                "size": 4,
                "source": {
                    "kind": "neetcode_site_data",
                    "url": "https://example.test/tiny",
                    "retrieved_on": "2026-10-29",
                },
                "groups": [
                    {
                        "name": "All",
                        "problems": [
                            {"id": 1, "slug": "two-sum"},
                            {"id": 2, "slug": "problem-2"},
                            {"id": 4, "slug": "problem-4"},
                            {"id": 5, "slug": "problem-5"},
                        ],
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    shutil.copytree(REPO_ROOT / "problems" / "leetcode-1", work.problems / "leetcode-1")
    assert work.run("plan").returncode == 0
    report = json.loads(work.run("report", "--json").stdout)
    tiny = next(item for item in report["lists"] if item["id"] == "tiny")
    assert tiny["size"] == 4
    assert tiny["counts"] == {"ready": 1, "in_progress": 0, "blocked": 2, "pending": 1}
    assert "tiny" in work.run("report").stdout


def test_render_gives_a_reviewable_ticket_body(work: Workspace) -> None:
    assert work.run("plan").returncode == 0
    result = work.run("render", "arrays-easy-01")
    assert result.returncode == 0, result.stderr
    body = result.stdout
    assert "Prepare arrays problems, easy (1 of 2)" in body
    assert "- [ ] 2 Problem 2 (easy, problem-2)" in body
    assert "- [ ] 13 Problem 13 (easy, problem-13)" in body
    assert "Sub-issue of #1" in body and "#15" in body
    assert "independent correctness evidence" in body  # The readiness bar from #1.
    assert "Local validation and LeetCode acceptance stay separate" in body


def test_render_lists_the_concept_prerequisites_in_curriculum_order(
    work: Workspace,
) -> None:
    assert work.run("plan").returncode == 0
    body = work.run("render", "dp-hard-01").stdout
    assert "Prerequisites" in body
    for concept in (
        "arrays",
        "strings",
        "lookup",
        "sequences",
        "linked",
        "trees",
        "graphs",
    ):
        assert concept in body.lower()


def test_render_of_a_blocked_class_states_the_blocker(work: Workspace) -> None:
    assert work.run("plan").returncode == 0
    body = work.run("render", "premium-01").stdout
    assert "Blocked" in body
    assert "Premium problems cannot be read without a subscription." in body
    assert "stay blocked" in body


def test_render_of_an_unknown_class_names_the_known_ones(work: Workspace) -> None:
    assert work.run("plan").returncode == 0
    result = work.run("render", "nope")
    assert result.returncode == 1
    assert "no ticket named 'nope'" in result.stderr
    assert "arrays-easy-01" in result.stderr
