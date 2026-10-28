# ABOUTME: Exercises configured lint and type gates against real Python files.
# ABOUTME: Verifies that valid code passes and representative defects fail.

import subprocess
import sys
from pathlib import Path

import pytest


@pytest.mark.parametrize(
    ("source", "expected_code", "diagnostic"),
    [
        ("def answer() -> int:\n    return 42\n", 0, "Success"),
        ("def answer():\n    return 42\n", 1, "no-untyped-def"),
    ],
)
def test_strict_typing_checks_real_code(
    tmp_path: Path, source: str, expected_code: int, diagnostic: str
) -> None:
    root = Path(__file__).resolve().parents[2]
    sample = tmp_path / "sample.py"
    sample.write_text(source, encoding="utf-8")
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "mypy",
            "--config-file",
            str(root / "pyproject.toml"),
            "--no-incremental",
            str(sample),
        ],
        capture_output=True,
        text=True,
        timeout=60,
        check=False,
    )
    assert result.returncode == expected_code, result.stdout + result.stderr
    assert diagnostic in result.stdout
    assert result.stderr == ""


@pytest.mark.parametrize(
    ("source", "expected_code", "diagnostic"),
    [
        ("answer = 42\n", 0, "All checks passed"),
        ("answer = missing_name\n", 1, "F821"),
    ],
)
def test_linter_checks_real_code(
    tmp_path: Path, source: str, expected_code: int, diagnostic: str
) -> None:
    root = Path(__file__).resolve().parents[2]
    sample = tmp_path / "sample.py"
    sample.write_text(source, encoding="utf-8")
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "ruff",
            "check",
            "--config",
            str(root / "pyproject.toml"),
            str(sample),
        ],
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )
    assert result.returncode == expected_code, result.stdout + result.stderr
    assert diagnostic in result.stdout
    assert result.stderr == ""
