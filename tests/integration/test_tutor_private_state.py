# ABOUTME: Integration tests for the private-state checks in real temporary Git repos.
# ABOUTME: They run the real git command to confirm .practice is ignored and untracked.

import subprocess
from pathlib import Path

from practice.tutor_policy import check_private_state


def git(root: Path, *args: str) -> None:
    subprocess.run(["git", "-C", str(root), *args], check=True, capture_output=True)


def make_repo(root: Path, gitignore: str | None) -> Path:
    root.mkdir()
    git(root, "init", "-q")
    if gitignore is not None:
        (root / ".gitignore").write_text(gitignore, encoding="utf-8")
    return root


def test_ignored_and_untracked_practice_directory_passes(tmp_path: Path) -> None:
    repo = make_repo(tmp_path / "repo", ".practice/\n")
    assert check_private_state(repo) == []


def test_missing_ignore_rule_is_reported(tmp_path: Path) -> None:
    repo = make_repo(tmp_path / "repo", "__pycache__/\n")
    problems = check_private_state(repo)
    assert any("not ignored" in problem for problem in problems)


def test_ignore_that_only_lives_in_the_local_exclude_file_is_reported(
    tmp_path: Path,
) -> None:
    repo = make_repo(tmp_path / "repo", None)
    (repo / ".git" / "info" / "exclude").write_text(".practice/\n", encoding="utf-8")
    problems = check_private_state(repo)
    assert any(".gitignore" in problem for problem in problems)


def test_a_tracked_practice_file_is_reported(tmp_path: Path) -> None:
    repo = make_repo(tmp_path / "repo", ".practice/\n")
    (repo / ".practice").mkdir()
    (repo / ".practice" / "journal.jsonl").write_text("{}\n", encoding="utf-8")
    git(repo, "add", "-f", ".practice/journal.jsonl")
    problems = check_private_state(repo)
    assert any(
        "tracked" in problem and "journal.jsonl" in problem for problem in problems
    )


def test_a_directory_that_is_not_a_repository_is_reported(tmp_path: Path) -> None:
    plain = tmp_path / "plain"
    plain.mkdir()
    problems = check_private_state(plain)
    assert any("not a Git repository" in problem for problem in problems)
