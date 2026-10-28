# ABOUTME: Verifies locked setup and quality checks in an independent checkout.
# ABOUTME: Runs the actual development tools without copying an existing environment.

import os
import shutil
import subprocess
import sys
from pathlib import Path


def test_clean_checkout_runs_locked_checks(tmp_path: Path) -> None:
    root = Path(__file__).resolve().parents[2]
    checkout = tmp_path / "checkout"
    checkout.mkdir()
    for name in ("pyproject.toml", "uv.lock", ".python-version", "README.md"):
        shutil.copy2(root / name, checkout / name)
    for folder in ("src", "catalog"):
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
    ]
    for command in commands:
        result = subprocess.run(
            command,
            cwd=checkout,
            env=environment,
            capture_output=True,
            text=True,
            timeout=120,
            check=False,
        )
        assert result.returncode == 0, f"{command!r}\n{result.stdout}\n{result.stderr}"
        assert "warning:" not in result.stderr.lower(), result.stderr
    assert not (checkout / ".practice").exists()
