# ABOUTME: Runs the worker script in a bounded child process and collects its events.
# ABOUTME: On timeout the whole process tree is killed, on Windows and POSIX alike.

import json
import os
import signal
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any

WORKER = Path(__file__).with_name("_worker.py")
STDERR_TAIL_BYTES = 2000


@dataclass(frozen=True)
class ChildReport:
    events: list[dict[str, Any]]
    timed_out: bool
    exit_code: int | None  # None when the child had to be killed.
    stderr_tail: str


def run_worker(solution: Path, payload: dict[str, Any], timeout: float) -> ChildReport:
    # ignore_cleanup_errors: a just-killed process can briefly hold the directory.
    with tempfile.TemporaryDirectory(
        prefix="practice-run-", ignore_cleanup_errors=True
    ) as scratch:
        work = Path(scratch)
        payload_path = work / "payload.json"
        payload_path.write_text(json.dumps(payload), encoding="utf-8")
        events_path = work / "events.jsonl"
        stderr_path = work / "stderr.txt"
        command = [
            sys.executable,
            "-I",  # Isolated: ignore PYTHON* variables, user site and the cwd.
            str(WORKER),
            str(payload_path),
            str(solution.resolve()),
        ]
        with events_path.open("wb") as events_file, stderr_path.open("wb") as errors:
            process = subprocess.Popen(
                command,
                stdin=subprocess.DEVNULL,
                stdout=events_file,
                stderr=errors,
                cwd=work,
                **_own_process_group(),
            )
            timed_out = False
            try:
                process.wait(timeout=timeout)
            except subprocess.TimeoutExpired:
                timed_out = True
                kill_process_tree(process)
                process.wait()
        return ChildReport(
            events=_read_events(events_path),
            timed_out=timed_out,
            exit_code=None if timed_out else process.returncode,
            stderr_tail=_read_tail(stderr_path),
        )


def _own_process_group() -> dict[str, Any]:
    """Put the child in its own group so the whole tree can be stopped."""
    if sys.platform == "win32":
        return {"creationflags": subprocess.CREATE_NEW_PROCESS_GROUP}
    else:
        return {"start_new_session": True}


def kill_process_tree(process: subprocess.Popen[bytes]) -> None:
    if sys.platform == "win32":
        # /T also ends children, and the launcher python.exe that uv venvs use.
        subprocess.run(
            ["taskkill", "/F", "/T", "/PID", str(process.pid)],
            capture_output=True,
            check=False,
        )
        process.kill()
    else:
        try:
            os.killpg(process.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass


def _read_events(path: Path) -> list[dict[str, Any]]:
    events: list[dict[str, Any]] = []
    for line in path.read_text(encoding="ascii", errors="replace").splitlines():
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue  # A kill can cut the last line short.
        if isinstance(event, dict):
            events.append(event)
    return events


def _read_tail(path: Path) -> str:
    with path.open("rb") as handle:
        handle.seek(0, os.SEEK_END)
        handle.seek(max(0, handle.tell() - STDERR_TAIL_BYTES))
        return handle.read().decode("utf-8", errors="replace")
