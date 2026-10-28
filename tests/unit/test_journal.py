# ABOUTME: Unit tests for the append-only journal against real files in a temp dir.
# ABOUTME: Covers complete-line writes, torn trailing records and malformed lines.

import json
from pathlib import Path

import pytest

from practice.journal import SCHEMA_VERSION, Journal, JournalError


@pytest.fixture
def journal(tmp_path: Path) -> Journal:
    return Journal(tmp_path / "learner" / "journal.jsonl")


def test_reading_a_missing_journal_is_empty_and_creates_nothing(
    journal: Journal,
) -> None:
    contents = journal.read()

    assert contents.records == []
    assert contents.problems == []
    assert not journal.path.parent.exists()


def test_append_writes_one_complete_json_line(journal: Journal) -> None:
    record = journal.append("attempt_started", attempt_id="a1", note="line\nbreak")

    raw = journal.path.read_bytes()
    assert raw.endswith(b"\n")
    assert raw.count(b"\n") == 1
    stored = json.loads(raw)
    assert stored == record
    assert stored["schema_version"] == SCHEMA_VERSION
    assert stored["type"] == "attempt_started"
    assert stored["attempt_id"] == "a1"
    assert stored["note"] == "line\nbreak"
    assert stored["event_id"]
    assert stored["at"].endswith("+00:00")


def test_records_read_back_in_order(journal: Journal) -> None:
    for number in range(5):
        journal.append("tick", number=number)

    contents = journal.read()

    assert [r["number"] for r in contents.records] == [0, 1, 2, 3, 4]
    assert len({r["event_id"] for r in contents.records}) == 5
    assert contents.problems == []


def test_non_ascii_text_round_trips(journal: Journal) -> None:
    journal.append("note", text="café ☃")

    assert journal.read().records[0]["text"] == "café ☃"


def test_reserved_field_names_are_rejected(journal: Journal) -> None:
    with pytest.raises(JournalError, match="reserved"):
        journal.append("tick", event_id="mine")

    assert not journal.path.exists()


def test_torn_trailing_record_is_reported_not_dropped(journal: Journal) -> None:
    journal.append("tick", number=1)
    with journal.path.open("ab") as handle:
        handle.write(b'{"schema_version":1,"event_id":"x","at":"2026-')

    contents = journal.read()

    assert [r["number"] for r in contents.records] == [1]
    assert len(contents.problems) == 1
    assert contents.problems[0].line_number == 2
    assert "interrupted" in contents.problems[0].message


def test_append_after_a_torn_record_starts_a_fresh_line(journal: Journal) -> None:
    journal.append("tick", number=1)
    torn = b'{"schema_version":1,"event_id":"x"'
    with journal.path.open("ab") as handle:
        handle.write(torn)
    before = journal.path.read_bytes()

    journal.append("tick", number=2)

    contents = journal.read()
    assert [r["number"] for r in contents.records] == [1, 2]
    assert [p.line_number for p in contents.problems] == [2]
    assert journal.path.read_bytes().startswith(before)  # History is never rewritten.
    assert torn in journal.path.read_bytes()


def test_complete_record_missing_only_its_newline_is_kept(journal: Journal) -> None:
    journal.append("tick", number=1)
    journal.path.write_bytes(journal.path.read_bytes().rstrip(b"\n"))

    journal.append("tick", number=2)

    contents = journal.read()
    assert [r["number"] for r in contents.records] == [1, 2]
    assert contents.problems == []


def test_malformed_middle_line_is_reported_and_neighbours_survive(
    journal: Journal,
) -> None:
    journal.append("tick", number=1)
    with journal.path.open("ab") as handle:
        handle.write(b"this is not json\n")
    journal.append("tick", number=3)

    contents = journal.read()

    assert [r["number"] for r in contents.records] == [1, 3]
    assert [p.line_number for p in contents.problems] == [2]
    assert "not valid JSON" in contents.problems[0].message


@pytest.mark.parametrize(
    ("line", "fragment"),
    [
        (b"[1, 2]", "JSON object"),
        (b'{"schema_version":1}', "event_id"),
        (b'{"schema_version":99,"event_id":"a","at":"t","type":"x"}', "version 99"),
        (b'{"event_id":"a","at":"t","type":"x"}', "schema_version"),
        (b"\xff\xfe broken bytes", "UTF-8"),
    ],
)
def test_invalid_records_are_reported_with_a_reason(
    journal: Journal, line: bytes, fragment: str
) -> None:
    journal.path.parent.mkdir(parents=True)
    journal.path.write_bytes(line + b"\n")

    contents = journal.read()

    assert contents.records == []
    assert len(contents.problems) == 1
    assert fragment in contents.problems[0].message


def test_blank_lines_hold_no_history_and_are_ignored(journal: Journal) -> None:
    journal.append("tick", number=1)
    with journal.path.open("ab") as handle:
        handle.write(b"\n   \n")

    contents = journal.read()

    assert len(contents.records) == 1
    assert contents.problems == []
