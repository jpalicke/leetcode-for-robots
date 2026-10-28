# ABOUTME: Shared pytest fixtures that locate the Two Sum runner fixture package.
# ABOUTME: Also builds small throwaway exercise packages in a temporary directory.

import json
from collections.abc import Callable
from pathlib import Path
from typing import Any

import pytest

FIXTURES = Path(__file__).resolve().parent / "fixtures"


@pytest.fixture
def two_sum_package() -> Path:
    return FIXTURES / "two_sum"


@pytest.fixture
def two_sum_solution() -> Callable[[str], Path]:
    def locate(name: str) -> Path:
        return FIXTURES / "two_sum_solutions" / f"{name}.py"

    return locate


@pytest.fixture
def make_package(tmp_path: Path) -> Callable[..., Path]:
    """Write a package directory; pass suite=None to leave out the test suite."""

    def build(metadata: dict[str, Any], suite: dict[str, Any] | None = None) -> Path:
        package = tmp_path / "package"
        package.mkdir()
        (package / "problem.json").write_text(json.dumps(metadata), encoding="utf-8")
        if suite is not None:
            (package / "tests.json").write_text(json.dumps(suite), encoding="utf-8")
        return package

    return build
