# ABOUTME: Appends to one journal from several real processes at the same time.
# ABOUTME: Every record must survive intact, with no interleaved or torn lines.

import subprocess
import sys
from pathlib import Path

from practice.journal import Journal

WRITER = """
import sys
from pathlib import Path

from practice.journal import Journal

path, writer = Path(sys.argv[1]), sys.argv[2]
count, size = int(sys.argv[3]), int(sys.argv[4])
journal = Journal(path)
for number in range(count):
    journal.append("tick", writer=writer, number=number, filler="x" * size)
"""

PROCESSES = 6
APPENDS_EACH = 25
FILLER_BYTES = 20_000  # Large enough that unlocked appends would interleave.


def test_concurrent_processes_never_corrupt_or_lose_records(tmp_path: Path) -> None:
    script = tmp_path / "writer.py"
    script.write_text(WRITER, encoding="utf-8")
    journal_path = tmp_path / "learner" / "journal.jsonl"
    command = [sys.executable, str(script), str(journal_path)]
    writers = [
        subprocess.Popen(
            [*command, f"w{index}", str(APPENDS_EACH), str(FILLER_BYTES)],
            stderr=subprocess.PIPE,
            text=True,
        )
        for index in range(PROCESSES)
    ]
    for writer in writers:
        _, errors = writer.communicate(timeout=120)
        assert writer.returncode == 0, errors

    contents = Journal(journal_path).read()

    assert contents.problems == []
    assert len(contents.records) == PROCESSES * APPENDS_EACH
    assert len({r["event_id"] for r in contents.records}) == PROCESSES * APPENDS_EACH
    for index in range(PROCESSES):
        numbers = [r["number"] for r in contents.records if r["writer"] == f"w{index}"]
        assert numbers == list(range(APPENDS_EACH))  # Each writer's order is kept.
    assert all(len(r["filler"]) == FILLER_BYTES for r in contents.records)


def test_a_torn_record_from_a_dead_writer_does_not_block_other_writers(
    tmp_path: Path,
) -> None:
    journal_path = tmp_path / "journal.jsonl"
    journal = Journal(journal_path)
    journal.append("tick", writer="before", number=0)
    with journal_path.open("ab") as handle:
        handle.write(b'{"schema_version":1,"event_id":"dead","at":"2026-10-2')
    script = tmp_path / "writer.py"
    script.write_text(WRITER, encoding="utf-8")

    done = subprocess.run(
        [sys.executable, str(script), str(journal_path), "after", "3", "10"],
        capture_output=True,
        text=True,
        timeout=60,
        check=False,
    )

    assert done.returncode == 0, done.stderr
    contents = journal.read()
    assert [r["writer"] for r in contents.records] == [
        "before",
        "after",
        "after",
        "after",
    ]
    assert [p.line_number for p in contents.problems] == [2]
