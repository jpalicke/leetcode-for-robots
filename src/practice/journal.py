# ABOUTME: Append-only JSON Lines journal of learner events, safe across processes.
# ABOUTME: Reads report damaged lines; history is never rewritten or dropped.

import json
import os
import sys
import time
import uuid
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import IO, Any

SCHEMA_VERSION = 1
RESERVED_FIELDS = ("schema_version", "event_id", "at", "type")
LOCK_TIMEOUT_SECONDS = 30.0
LOCK_POLL_SECONDS = 0.01


class JournalError(Exception):
    """The journal cannot be written."""


@dataclass(frozen=True)
class JournalProblem:
    line_number: int
    message: str


@dataclass(frozen=True)
class JournalContents:
    records: list[dict[str, Any]]
    problems: list[JournalProblem]


class Journal:
    def __init__(self, path: Path) -> None:
        self.path = path

    def append(self, event_type: str, **fields: Any) -> dict[str, Any]:
        """Write one complete record as a single line and flush it to disk."""
        clashes = [name for name in fields if name in RESERVED_FIELDS]
        if clashes:
            raise JournalError(f"reserved journal field names: {', '.join(clashes)}")
        record: dict[str, Any] = {
            "schema_version": SCHEMA_VERSION,
            "event_id": uuid.uuid4().hex,
            "at": datetime.now(UTC).isoformat(timespec="milliseconds"),
            "type": event_type,
            **fields,
        }
        line = json.dumps(record, ensure_ascii=True, separators=(",", ":")) + "\n"
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            with _exclusive(self.path.with_name(self.path.name + ".lock")):
                with self.path.open("a+b") as handle:
                    # A torn tail from an interrupted write has no newline. Start on a
                    # fresh line so the torn text stays one reportable line of its own
                    # and this record is never glued to it.
                    prefix = b"" if _ends_a_line(handle) else b"\n"
                    handle.write(prefix + line.encode("ascii"))
                    handle.flush()
                    os.fsync(handle.fileno())
        except OSError as error:
            raise JournalError(f"cannot write {self.path}: {error}") from error
        return record

    def read(self) -> JournalContents:
        """Return every valid record plus a report of each line that is not one."""
        try:
            data = self.path.read_bytes()
        except FileNotFoundError:
            return JournalContents([], [])
        except OSError as error:
            raise JournalError(f"cannot read {self.path}: {error}") from error
        unterminated_tail = bool(data) and not data.endswith(b"\n")
        lines = data.split(b"\n")
        if lines and lines[-1] == b"":
            lines.pop()  # The text after the final newline; nothing follows it.

        records: list[dict[str, Any]] = []
        problems: list[JournalProblem] = []
        for number, raw in enumerate(lines, start=1):
            if not raw.strip():
                continue  # A blank line holds no history.
            record, reason = _parse_line(raw)
            if record is None:
                if unterminated_tail and number == len(lines):
                    reason += (
                        "; this unterminated final line is probably an "
                        "interrupted write"
                    )
                problems.append(JournalProblem(number, reason))
            else:
                records.append(record)
        return JournalContents(records, problems)


def _ends_a_line(handle: IO[bytes]) -> bool:
    size = handle.seek(0, os.SEEK_END)
    if size == 0:
        return True
    handle.seek(-1, os.SEEK_END)
    return handle.read(1) == b"\n"


def _parse_line(raw: bytes) -> tuple[dict[str, Any] | None, str]:
    try:
        data = json.loads(raw.decode("utf-8"))
    except UnicodeDecodeError:
        return None, "the line is not valid UTF-8"
    except json.JSONDecodeError as error:
        return None, f"the line is not valid JSON ({error.msg})"
    if not isinstance(data, dict):
        return None, "the line is not a JSON object"
    version = data.get("schema_version")
    if not isinstance(version, int) or isinstance(version, bool):
        return None, "the record has no integer schema_version"
    if version != SCHEMA_VERSION:
        return None, f"the record uses unsupported schema version {version}"
    for name in ("event_id", "at", "type"):
        if not isinstance(data.get(name), str) or not data[name]:
            return None, f"the record has no {name}"
    return data, ""


@contextmanager
def _exclusive(lock_path: Path) -> Iterator[None]:
    """Hold an operating system lock; it is released if the holder dies."""
    with lock_path.open("a+b") as handle:
        _acquire(handle)
        try:
            yield
        finally:
            _release(handle)


if sys.platform == "win32":
    import msvcrt

    def _acquire(handle: IO[bytes]) -> None:
        deadline = time.monotonic() + LOCK_TIMEOUT_SECONDS
        while True:
            handle.seek(0)
            try:
                msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
                return
            except OSError:
                if time.monotonic() > deadline:
                    raise
                time.sleep(LOCK_POLL_SECONDS)

    def _release(handle: IO[bytes]) -> None:
        handle.seek(0)
        msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)

else:
    import fcntl

    def _acquire(handle: IO[bytes]) -> None:
        fcntl.flock(handle.fileno(), fcntl.LOCK_EX)

    def _release(handle: IO[bytes]) -> None:
        fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
