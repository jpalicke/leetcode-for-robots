# ABOUTME: Supports independent development verification in portable temporary paths.
# ABOUTME: Bounds real command execution and reports captured process-tree failures.

import os
import signal
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any


def check_windows_path(root: Path, references: Path, *, extra: int = 0) -> None:
    """Reject unsupported destinations before a partial Windows reference copy."""
    if sys.platform == "win32":
        check_path_budget(root, references, extra=extra)


def check_path_budget(root: Path, references: Path, *, extra: int = 0) -> None:
    """Reject a destination whose longest reference path reaches 260 code units."""
    longest = max(
        (
            path.relative_to(references.parent)
            for path in references.rglob("*")
            if path.is_file()
            and "__pycache__" not in path.relative_to(references).parts
        ),
        key=lambda path: len(str(path).encode("utf-16-le")) // 2,
    )
    destination = root.resolve() / longest
    if len(str(destination).encode("utf-16-le")) // 2 + extra >= 260:
        raise AssertionError(
            "Windows verification path exceeds the portable "
            "259 UTF-16 code-unit limit: "
            f"{destination} (plus {extra} UTF-16 code units "
            "reserved for test subfolders). "
            "Set TEMP and TMP to a shorter writable directory before starting pytest; "
            "for pytest fixture paths, --basetemp may also select a shorter directory. "
            "Clean-checkout workspaces use TEMP/TMP, independently of --basetemp."
        )


def own_process_group() -> dict[str, Any]:
    """Put the check in its own group so the whole tree can be stopped."""
    if sys.platform == "win32":
        return {"creationflags": subprocess.CREATE_NEW_PROCESS_GROUP}
    else:
        return {"start_new_session": True}


def run_check(
    command: list[str], cwd: Path, environment: dict[str, str], timeout: float
) -> None:
    """Run a check with file capture so descendants cannot hold output pipes open."""
    with tempfile.TemporaryFile() as output, tempfile.TemporaryFile() as errors:
        process = subprocess.Popen(
            command,
            cwd=cwd,
            env=environment,
            stdin=subprocess.DEVNULL,
            stdout=output,
            stderr=errors,
            **own_process_group(),
        )
        failure = ""
        try:
            process.wait(timeout=timeout)
        except subprocess.TimeoutExpired:
            failure = f"timed out after {timeout}s"
            try:
                if sys.platform == "win32":
                    cleanup = subprocess.run(
                        ["taskkill", "/F", "/T", "/PID", str(process.pid)],
                        capture_output=True,
                        timeout=10,
                        check=False,
                    )
                    if cleanup.returncode:
                        failure += (
                            f"; tree cleanup failed: {cleanup.stdout!r} "
                            f"{cleanup.stderr!r}"
                        )
                else:
                    os.killpg(process.pid, signal.SIGKILL)
            except (OSError, subprocess.TimeoutExpired) as error:
                failure += f"; tree cleanup failed: {error}"
            finally:
                if process.poll() is None:
                    process.kill()
                try:
                    process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    failure += "; launcher did not exit after kill"
        output.seek(0)
        errors.seek(0)
        stdout = output.read().decode("utf-8", errors="replace")
        stderr = errors.read().decode("utf-8", errors="replace")
    if failure or process.returncode:
        raise AssertionError(
            f"{command!r}: {failure or f'exit {process.returncode}'}\n"
            f"stdout:\n{stdout}\nstderr:\n{stderr}"
        )
    assert "warning:" not in stderr.lower(), f"{command!r}\n{stderr}"
