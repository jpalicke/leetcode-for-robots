# ABOUTME: Verifies locked setup and quality checks in an independent checkout.
# ABOUTME: Runs the actual development tools without copying an existing environment.

import os
import shutil
import sys
import tempfile
from pathlib import Path

from tools.verification import check_windows_path, run_check


def test_clean_checkout_runs_locked_checks() -> None:
    root = Path(__file__).resolve().parents[2]
    with tempfile.TemporaryDirectory(prefix="lc-") as temporary:
        _check_checkout(root, Path(temporary))


def _check_checkout(root: Path, checkout: Path) -> None:
    check_windows_path(checkout, root / "references")
    for name in ("pyproject.toml", "uv.lock", ".python-version", "README.md"):
        shutil.copy2(root / name, checkout / name)
    for folder in (
        "src",
        "catalog",
        "curriculum",
        "problems",
        "references",
        "tools",
        "experiments",
    ):
        shutil.copytree(
            root / folder,
            checkout / folder,
            ignore=shutil.ignore_patterns("__pycache__"),
        )
    for layer in ("unit", "integration", "fixtures"):
        shutil.copytree(
            root / "tests" / layer,
            checkout / "tests" / layer,
            ignore=shutil.ignore_patterns("__pycache__"),
        )
    shutil.copy2(root / "tests" / "conftest.py", checkout / "tests" / "conftest.py")

    uv = shutil.which("uv")
    assert uv is not None, "Install uv before running the development suite"
    environment = os.environ.copy()
    environment.pop("VIRTUAL_ENV", None)
    environment["UV_PROJECT_ENVIRONMENT"] = str(checkout / ".venv")
    environment["UV_PYTHON"] = sys.executable
    environment["UV_PYTHON_DOWNLOADS"] = "never"
    # Sync may download into the uv cache; later steps then run fully offline.
    commands = [
        [uv, "sync", "--locked"],
        [uv, "run", "--locked", "--offline", "ruff", "check", "."],
        [uv, "run", "--locked", "--offline", "ruff", "format", "--check", "."],
        [uv, "run", "--locked", "--offline", "mypy"],
        [uv, "run", "--locked", "--offline", "pytest"],
        [uv, "run", "--locked", "--offline", "practice", "search", "two sum"],
        [
            uv,
            "run",
            "--locked",
            "--offline",
            "practice",
            "run",
            "tests/fixtures/two_sum",
            "tests/fixtures/two_sum_solutions/correct_hash_map.py",
        ],
        [uv, "run", "--locked", "--offline", "practice", "progress"],
        [uv, "run", "--locked", "--offline", "practice", "curriculum", "check"],
        [uv, "run", "--locked", "--offline", "practice", "curriculum", "next"],
        [
            uv,
            "run",
            "--locked",
            "--offline",
            "practice",
            "knowledge",
            "export",
            "leetcode",
            "1",
        ],
    ]
    for command in commands:
        # The full nested test suite needs a separate bound from short checks.
        command_timeout = 600 if command[-1] == "pytest" else 120
        run_check(command, checkout, environment, command_timeout)
    assert not (checkout / ".practice").exists()
