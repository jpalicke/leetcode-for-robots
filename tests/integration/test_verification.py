# ABOUTME: Exercises verification commands against real files and process trees.
# ABOUTME: Checks timeout diagnostics, descendant cleanup and failed command output.

import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

import pytest

from tools.verification import run_check


def test_failed_check_reports_both_output_streams(tmp_path: Path) -> None:
    with pytest.raises(AssertionError, match="exit 7") as failure:
        run_check(
            [
                sys.executable,
                "-c",
                "import sys; print('out'); print('err', file=sys.stderr); sys.exit(7)",
            ],
            tmp_path,
            os.environ.copy(),
            10,
        )
    assert "out" in str(failure.value)
    assert "err" in str(failure.value)


@pytest.mark.parametrize("launcher", ["python", "uv"])
def test_timeout_stops_children_and_grandchildren(
    tmp_path: Path, launcher: str
) -> None:
    script = tmp_path / "tree.py"
    script.write_text(
        "import os, pathlib, subprocess, sys, time\n"
        "root = pathlib.Path(sys.argv[1])\n"
        "depth = int(sys.argv[2])\n"
        "(root / f'pid{depth}').write_text(str(os.getpid()))\n"
        "if depth:\n"
        " subprocess.Popen([sys.executable, __file__, str(root), str(depth-1)])\n"
        "print(f'ready{depth}', flush=True)\n"
        "print(f'error{depth}', file=sys.stderr, flush=True)\n"
        "until = time.monotonic() + 20\n"
        "while time.monotonic() < until:\n"
        " (root / f'beat{depth}').write_text(str(time.monotonic()))\n"
        " time.sleep(0.05)\n",
        encoding="utf-8",
    )
    command = [sys.executable, str(script), str(tmp_path), "2"]
    if launcher == "uv":
        uv = shutil.which("uv")
        assert uv is not None
        root = Path(__file__).resolve().parents[2]
        command = [uv, "run", "--locked", "--offline", "--project", str(root), *command]
    try:
        started = time.monotonic()
        with pytest.raises(AssertionError, match="timed out") as failure:
            run_check(command, tmp_path, os.environ.copy(), 3)
        assert time.monotonic() - started < 15
        assert repr(str(script)) in str(failure.value)
        assert "3s" in str(failure.value)
        assert "ready0" in str(failure.value)
        assert "error0" in str(failure.value)
        assert "cleanup failed" not in str(failure.value)
        beats = [(tmp_path / f"beat{depth}").read_text() for depth in range(3)]
        time.sleep(0.3)
        assert beats == [(tmp_path / f"beat{depth}").read_text() for depth in range(3)]
        for depth in range(3):
            pid = int((tmp_path / f"pid{depth}").read_text())
            if sys.platform == "win32":
                result = subprocess.run(
                    ["tasklist", "/FI", f"PID eq {pid}", "/NH", "/FO", "CSV"],
                    capture_output=True,
                    text=True,
                    check=True,
                    timeout=10,
                )
                assert f'"{pid}"' not in result.stdout
            else:
                # A reaped child has no proc entry; an orphan zombie cannot execute.
                status = Path(f"/proc/{pid}/stat")
                assert not status.exists() or status.read_text().split()[2] == "Z"
    finally:
        for path in tmp_path.glob("pid*"):
            pid = int(path.read_text())
            if sys.platform == "win32":
                subprocess.run(
                    ["taskkill", "/F", "/T", "/PID", str(pid)],
                    capture_output=True,
                    check=False,
                    timeout=10,
                )
            else:
                try:
                    os.kill(pid, 9)
                except ProcessLookupError:
                    pass
