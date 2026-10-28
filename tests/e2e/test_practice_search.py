# ABOUTME: End-to-end tests that run the installed practice command in a subprocess.
# ABOUTME: Uses the committed snapshot and a deliberately corrupted copy of it.

import subprocess
import sys
from pathlib import Path

from practice.catalog import DEFAULT_CATALOG_PATH


def run_practice(*args: str) -> subprocess.CompletedProcess[str]:
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
        timeout=60,
        check=False,
    )


def test_title_and_id_searches_show_the_same_entry() -> None:
    by_title = run_practice("search", "two sum")
    by_id = run_practice("search", "1")

    assert by_title.returncode == 0
    assert by_id.returncode == 0
    assert by_title.stderr == ""
    assert by_id.stderr == ""
    assert by_id.stdout.splitlines()[0] == by_title.stdout.splitlines()[0]
    assert "Two Sum" in by_id.stdout


def test_slug_search_finds_the_entry() -> None:
    result = run_practice("search", "two-sum")

    assert result.returncode == 0
    assert result.stdout.count("\n") == 1
    assert "Two Sum" in result.stdout


def test_unknown_query_says_nothing_matches() -> None:
    result = run_practice("search", "zzzzqqqq-no-such-problem")

    assert result.returncode == 1
    assert "No LeetCode problems match" in result.stdout


def test_non_ascii_titles_print_without_crashing() -> None:
    result = run_practice("search", "knight")

    assert result.returncode == 0
    assert result.stderr == ""


def test_corrupted_copy_is_rejected_with_a_clear_error(tmp_path: Path) -> None:
    text = DEFAULT_CATALOG_PATH.read_text(encoding="utf-8")
    corrupted = tmp_path / "leetcode.json"
    corrupted.write_text(text[: len(text) // 2], encoding="utf-8")

    result = run_practice("--catalog", str(corrupted), "search", "two sum")

    assert result.returncode == 3
    assert result.stdout == ""
    assert "not valid JSON" in result.stderr
    assert "Traceback" not in result.stderr
