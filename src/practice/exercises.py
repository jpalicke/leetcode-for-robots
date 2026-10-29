# ABOUTME: Decides whether a problem has a ready exercise package; else it is pending.
# ABOUTME: Shared by the menus and the recommendation engine so they always agree.

from dataclasses import dataclass
from pathlib import Path

from practice.package import PackageError, load_package
from practice.readiness import check_readiness


@dataclass(frozen=True)
class Exercise:
    package_dir: Path
    ready: bool
    reason: str  # Why it is pending, starting with "Pending"; empty when ready.


def exercise_status(
    problems_dir: Path, references: Path, platform: str, problem_id: str
) -> Exercise:
    """Whether a problem has a ready package. Anything else is pending."""
    directory = problems_dir / f"{platform}-{problem_id}"
    if not directory.is_dir():
        return Exercise(directory, False, "Pending: no exercise package yet.")
    report = check_readiness(directory, references)
    if not report.ready:
        failing = ", ".join(check.name for check in report.checks if not check.ok)
        return Exercise(
            directory,
            False,
            f"Pending: the exercise is not ready (failing: {failing}).",
        )
    try:
        package = load_package(directory)
    except PackageError as error:
        return Exercise(directory, False, f"Pending: {error}.")
    if (package.platform, package.problem_id) != (platform, problem_id):
        return Exercise(
            directory,
            False,
            f"Pending: the package describes {package.platform} "
            f"{package.problem_id}, not {platform} {problem_id}.",
        )
    return Exercise(directory, True, "")
