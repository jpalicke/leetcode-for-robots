# ABOUTME: Integration tests loading real catalog files from disk and running the CLI.
# ABOUTME: Corruption cases are deliberately damaged copies of the committed snapshot.

from pathlib import Path

import pytest

from practice.catalog import DEFAULT_CATALOG_PATH, CatalogError, load_catalog
from practice.cli import main


def corrupted_copy(tmp_path: Path, text: str) -> Path:
    path = tmp_path / "leetcode.json"
    path.write_text(text, encoding="utf-8")
    return path


def real_text() -> str:
    return DEFAULT_CATALOG_PATH.read_text(encoding="utf-8")


def test_committed_snapshot_loads_from_disk() -> None:
    catalog = load_catalog(DEFAULT_CATALOG_PATH)

    assert len(catalog.entries) == 4096


def test_truncated_file_is_rejected(tmp_path: Path) -> None:
    text = real_text()
    path = corrupted_copy(tmp_path, text[: len(text) // 2])

    with pytest.raises(CatalogError, match="not valid JSON"):
        load_catalog(path)


def test_missing_file_is_rejected(tmp_path: Path) -> None:
    with pytest.raises(CatalogError, match="cannot read"):
        load_catalog(tmp_path / "absent.json")


def test_file_that_is_not_utf8_text_is_rejected(tmp_path: Path) -> None:
    path = tmp_path / "leetcode.json"
    path.write_bytes(b"\xff\xfe\x00garbage")

    with pytest.raises(CatalogError, match="cannot read"):
        load_catalog(path)


def test_duplicate_slug_in_file_is_rejected(tmp_path: Path) -> None:
    path = corrupted_copy(
        tmp_path, real_text().replace('"slug": "add-two-numbers"', '"slug": "two-sum"')
    )

    with pytest.raises(CatalogError, match="duplicate slug"):
        load_catalog(path)


def test_search_command_prints_the_entry(capsys: pytest.CaptureFixture[str]) -> None:
    code = main(["search", "1"])

    captured = capsys.readouterr()
    assert code == 0
    assert "Two Sum" in captured.out
    assert "easy" in captured.out
    assert captured.err == ""


def test_id_and_title_searches_show_the_same_entry(
    capsys: pytest.CaptureFixture[str],
) -> None:
    main(["search", "1"])
    by_id = capsys.readouterr().out.splitlines()[0]
    main(["search", "two sum"])
    by_title = capsys.readouterr().out.splitlines()[0]

    assert by_id == by_title


def test_premium_entries_are_flagged(capsys: pytest.CaptureFixture[str]) -> None:
    catalog = load_catalog(DEFAULT_CATALOG_PATH)
    premium = next(e for e in catalog.entries if e.paid_only)

    main(["search", str(premium.frontend_question_id)])

    assert "premium" in capsys.readouterr().out


def test_no_match_says_so_and_exits_one(capsys: pytest.CaptureFixture[str]) -> None:
    code = main(["search", "zzzzqqqq-no-such-problem"])

    assert code == 1
    assert "No LeetCode problems match" in capsys.readouterr().out


def test_long_results_are_capped(capsys: pytest.CaptureFixture[str]) -> None:
    code = main(["search", "a"])

    out = capsys.readouterr().out
    assert code == 0
    assert "more. Refine your query" in out


def test_corrupt_catalog_is_rejected_without_traceback(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    text = real_text()
    path = corrupted_copy(tmp_path, text[: len(text) // 2])

    code = main(["--catalog", str(path), "search", "two sum"])

    captured = capsys.readouterr()
    assert code == 3
    assert captured.out == ""
    assert "not valid JSON" in captured.err
    assert "Traceback" not in captured.err
