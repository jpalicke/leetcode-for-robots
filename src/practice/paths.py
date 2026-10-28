# ABOUTME: Locates learner state and exercise packages on disk.
# ABOUTME: Learner state defaults to the ignored .practice directory in the repository.

import os
from collections.abc import Mapping
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
PRACTICE_DIR_ENV = "PRACTICE_DIR"


def resolve_practice_dir(flag: Path | None, environment: Mapping[str, str]) -> Path:
    """The --practice-dir flag wins, then PRACTICE_DIR, then .practice/ in the repo."""
    if flag is not None:
        return Path(os.path.abspath(flag))
    from_environment = environment.get(PRACTICE_DIR_ENV)
    if from_environment:
        return Path(os.path.abspath(from_environment))
    return REPO_ROOT / ".practice"


def default_package_dir(platform: str, problem_id: str) -> Path:
    return REPO_ROOT / "problems" / f"{platform}-{problem_id}"
