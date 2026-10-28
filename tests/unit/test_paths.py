# ABOUTME: Unit tests for where learner state and exercise packages are located.
# ABOUTME: Learner state defaults to the repository's ignored directory.

from pathlib import Path

from practice.paths import (
    PRACTICE_DIR_ENV,
    REPO_ROOT,
    default_package_dir,
    resolve_practice_dir,
)


def test_default_learner_state_is_the_ignored_directory_in_the_repository() -> None:
    assert resolve_practice_dir(None, {}) == REPO_ROOT / ".practice"
    assert (REPO_ROOT / "pyproject.toml").is_file()


def test_environment_variable_overrides_the_default(tmp_path: Path) -> None:
    resolved = resolve_practice_dir(None, {PRACTICE_DIR_ENV: str(tmp_path / "env")})

    assert resolved == tmp_path / "env"


def test_flag_overrides_the_environment_variable(tmp_path: Path) -> None:
    resolved = resolve_practice_dir(
        tmp_path / "flag", {PRACTICE_DIR_ENV: str(tmp_path / "env")}
    )

    assert resolved == tmp_path / "flag"


def test_empty_environment_variable_is_ignored() -> None:
    assert resolve_practice_dir(None, {PRACTICE_DIR_ENV: ""}) == (
        REPO_ROOT / ".practice"
    )


def test_relative_paths_become_absolute() -> None:
    assert resolve_practice_dir(Path("somewhere"), {}).is_absolute()


def test_default_package_lives_under_problems_by_platform_and_id() -> None:
    assert default_package_dir("leetcode", "1") == (
        REPO_ROOT / "problems" / "leetcode-1"
    )
