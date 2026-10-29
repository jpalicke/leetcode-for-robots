# ABOUTME: Runs `practice lists` in a subprocess on the committed lists and packages.
# ABOUTME: Statuses must agree with `practice readiness`; bad files must be refused.

import json
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest

from practice.catalog import DEFAULT_CATALOG_PATH, load_catalog
from practice.lists import DEFAULT_LISTS_DIR, load_lists
from practice.paths import REPO_ROOT

STARTERS = {1, 217, 242, 20, 704, 121}
EXPECTED_LISTS = {
    "binary-search": 32,
    "blind-75": 75,
    "dynamic-programming": 46,
    "graph-theory": 36,
    "leetcode-75": 75,
    "neetcode-150": 150,
    "neetcode-all": 450,
    "programming-skills": 33,
    "top-100-liked": 100,
    "top-interview-150": 150,
}


def practice(*args: str) -> subprocess.CompletedProcess[str]:
    scripts = Path(sys.executable).parent
    command = next(
        path
        for name in ("practice.exe", "practice")
        if (path := scripts / name).exists()
    )
    return subprocess.run(
        [str(command), *args],
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=120,
        check=False,
    )


def committed() -> dict[str, Any]:
    lists = load_lists(DEFAULT_LISTS_DIR, load_catalog(DEFAULT_CATALOG_PATH))
    return {item.list_id: item for item in lists}


def test_the_committed_lists_have_the_published_sizes() -> None:
    assert {k: v.size for k, v in committed().items()} == EXPECTED_LISTS


def test_blind_75_is_inside_neetcode_150() -> None:
    blind = {p.frontend_question_id for p in committed()["blind-75"].problems}
    neetcode = {p.frontend_question_id for p in committed()["neetcode-150"].problems}
    assert blind <= neetcode


def test_the_summary_names_every_list_with_its_size() -> None:
    result = practice("lists")
    assert result.returncode == 0, result.stderr
    for list_id, size in EXPECTED_LISTS.items():
        line = next(x for x in result.stdout.splitlines() if x.startswith(list_id))
        assert str(size) in line


def test_the_summary_counts_match_the_data() -> None:
    result = practice("lists", "--json")
    assert result.returncode == 0, result.stderr
    summary = {item["id"]: item for item in json.loads(result.stdout)}
    assert set(summary) == set(EXPECTED_LISTS)
    for list_id, problem_list in committed().items():
        ids = {p.frontend_question_id for p in problem_list.problems}
        premium = {p.frontend_question_id for p in problem_list.problems if p.paid_only}
        counts = summary[list_id]["counts"]
        assert counts["ready"] == len(ids & STARTERS)
        assert counts["blocked"] == len(premium - STARTERS)
        assert sum(counts.values()) == problem_list.size


def test_show_prints_groups_in_order_with_a_status_on_every_problem() -> None:
    result = practice("lists", "show", "blind-75")
    assert result.returncode == 0, result.stderr
    first = result.stdout.splitlines()[0]
    assert first.startswith("Blind 75") and "75 problems" in first
    groups = [g.name for g in committed()["blind-75"].groups]
    positions = [result.stdout.index(f"\n{name}\n") for name in groups]
    assert positions == sorted(positions)
    problem_lines = [
        line for line in result.stdout.splitlines() if line.startswith("  [")
    ]
    assert len(problem_lines) == 75


def test_show_marks_ready_blocked_and_pending_correctly() -> None:
    lines = practice("lists", "show", "blind-75").stdout.splitlines()
    by_id = {int(line.split()[1]): line for line in lines if line.startswith("  [")}
    assert by_id[217].startswith("  [ready]")
    assert by_id[1].startswith("  [ready]")
    assert by_id[269].startswith("  [blocked]") and "premium" in by_id[269]
    assert by_id[15].startswith("  [pending]")  # 3Sum has no package yet.


def test_a_ready_problem_agrees_with_the_readiness_command() -> None:
    ready = practice("readiness", "leetcode", "217")
    assert ready.returncode == 0 and "READY" in ready.stdout
    shown = practice("lists", "show", "blind-75").stdout
    assert any(
        line.startswith("  [ready]") and " 217 " in line for line in shown.splitlines()
    )


def test_show_json_has_the_same_facts(tmp_path: Path) -> None:
    result = practice("lists", "show", "leetcode-75", "--json")
    assert result.returncode == 0, result.stderr
    data = json.loads(result.stdout)
    assert (data["id"], data["name"], data["size"]) == (
        "leetcode-75",
        "LeetCode 75",
        75,
    )
    assert data["source"]["kind"] == "leetcode_study_plan"
    assert sum(len(g["problems"]) for g in data["groups"]) == 75
    first = data["groups"][0]["problems"][0]
    assert {"id", "slug", "title", "difficulty", "status", "reason"} <= set(first)
    assert sum(data["counts"].values()) == 75


def test_pending_is_never_shown_as_ready() -> None:
    data = json.loads(practice("lists", "show", "neetcode-all", "--json").stdout)
    for group in data["groups"]:
        for problem in group["problems"]:
            if problem["status"] == "ready":
                assert problem["id"] in STARTERS
                assert problem["reason"] == ""
            else:
                assert problem["reason"]


def test_without_packages_nothing_is_ready(tmp_path: Path) -> None:
    empty = tmp_path / "problems"
    empty.mkdir()
    data = json.loads(practice("--problems-dir", str(empty), "lists", "--json").stdout)
    assert all(item["counts"]["ready"] == 0 for item in data)


def test_an_unknown_list_is_a_clear_error() -> None:
    result = practice("lists", "show", "nope")
    assert result.returncode == 1
    assert "no list named 'nope'" in result.stderr
    assert "blind-75" in result.stderr  # The known names are offered.


def test_check_accepts_the_committed_lists() -> None:
    result = practice("lists", "check")
    assert result.returncode == 0, result.stderr
    assert "10 lists valid" in result.stdout


def test_check_json() -> None:
    result = practice("lists", "check", "--json")
    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout) == {"valid": True, "lists": 10}


@pytest.fixture
def copied_lists(tmp_path: Path) -> Path:
    target = tmp_path / "lists"
    shutil.copytree(DEFAULT_LISTS_DIR, target)
    return target


def test_a_corrupted_file_is_refused_by_every_lists_command(
    copied_lists: Path,
) -> None:
    text = (copied_lists / "blind-75.json").read_text(encoding="utf-8")
    (copied_lists / "blind-75.json").write_text(
        text[: len(text) // 2], encoding="utf-8"
    )
    for args in (["lists"], ["lists", "show", "leetcode-75"], ["lists", "check"]):
        result = practice("--lists-dir", str(copied_lists), *args)
        assert result.returncode == 3, args
        assert "blind-75.json" in result.stderr and "not valid JSON" in result.stderr
        assert result.stdout == ""  # Nothing half-shown.


def test_a_list_naming_a_problem_the_catalog_lacks_is_refused(
    copied_lists: Path,
) -> None:
    path = copied_lists / "leetcode-75.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    data["groups"][0]["problems"][0] = {"id": 99999, "slug": "no-such-problem"}
    path.write_text(json.dumps(data), encoding="utf-8")
    result = practice("--lists-dir", str(copied_lists), "lists", "check")
    assert result.returncode == 3
    assert "problem 99999 is not in the catalog" in result.stderr


def test_a_missing_lists_folder_is_refused(tmp_path: Path) -> None:
    result = practice("--lists-dir", str(tmp_path / "nowhere"), "lists")
    assert result.returncode == 3
    assert "not a directory" in result.stderr


def test_an_empty_lists_folder_says_so(tmp_path: Path) -> None:
    empty = tmp_path / "empty"
    empty.mkdir()
    result = practice("--lists-dir", str(empty), "lists")
    assert result.returncode == 0
    assert "No lists" in result.stdout


def test_the_repository_root_is_where_the_lists_live() -> None:
    assert DEFAULT_LISTS_DIR == REPO_ROOT / "catalog" / "lists"
