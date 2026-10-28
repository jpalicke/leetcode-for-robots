# ABOUTME: Checks the repository's development configuration contract.
# ABOUTME: Keeps strict checking and test discovery explicit for contributors.

import tomllib
from pathlib import Path


def test_development_configuration_is_strict() -> None:
    root = Path(__file__).resolve().parents[2]
    config = tomllib.loads((root / "pyproject.toml").read_text(encoding="utf-8"))

    assert config["tool"]["mypy"]["strict"] is True
    assert config["tool"]["pytest"]["ini_options"]["filterwarnings"] == ["error"]
    assert config["tool"]["pytest"]["ini_options"]["testpaths"] == ["tests"]
    assert (root / "uv.lock").is_file()


def test_practice_command_is_installable_and_typed() -> None:
    root = Path(__file__).resolve().parents[2]
    config = tomllib.loads((root / "pyproject.toml").read_text(encoding="utf-8"))

    assert config["project"]["scripts"]["practice"] == "practice.cli:run"
    assert config["project"]["dependencies"] == []
    assert "src" in config["tool"]["mypy"]["files"]
