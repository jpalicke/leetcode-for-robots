# ABOUTME: End-to-end tests that run `practice tutor check` and `practice tutor start`.
# ABOUTME: Each failure mode is made in a throwaway Git repository copy of the contract.

import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
CONTRACT_PATHS = ("tutor", "CLAUDE.md", ".gitignore", ".cursor")


def run_practice(
    *args: str, practice_dir: Path | None = None
) -> subprocess.CompletedProcess[str]:
    scripts = Path(sys.executable).parent
    command = next(
        path
        for name in ("practice.exe", "practice")
        if (path := scripts / name).exists()
    )
    environment = {k: v for k, v in os.environ.items() if k != "PRACTICE_DIR"}
    if practice_dir is not None:
        environment["PRACTICE_DIR"] = str(practice_dir)
    return subprocess.run(
        [str(command), *args],
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=120,
        check=False,
        env=environment,
    )


@pytest.fixture
def contract_repo(tmp_path: Path) -> Path:
    """A real Git repository holding copies of the committed contract files."""
    repo = tmp_path / "repo"
    repo.mkdir()
    for name in CONTRACT_PATHS:
        source = REPO_ROOT / name
        if source.is_dir():
            shutil.copytree(source, repo / name)
        else:
            shutil.copy2(source, repo / name)
    subprocess.run(["git", "-C", str(repo), "init", "-q"], check=True)
    return repo


def check(repo: Path) -> subprocess.CompletedProcess[str]:
    return run_practice("tutor", "check", "--root", str(repo))


def append(path: Path, text: str) -> None:
    path.write_text(path.read_text(encoding="utf-8") + text, encoding="utf-8")


def test_the_committed_contract_passes() -> None:
    result = run_practice("tutor", "check")
    assert result.returncode == 0, result.stdout + result.stderr
    assert result.stderr == ""
    assert "Tutor contract ok" in result.stdout


def test_a_copy_of_the_contract_passes(contract_repo: Path) -> None:
    result = check(contract_repo)
    assert result.returncode == 0, result.stdout + result.stderr


def test_a_missing_policy_file_fails(contract_repo: Path) -> None:
    (contract_repo / "tutor" / "TUTOR.md").unlink()
    result = check(contract_repo)
    assert result.returncode == 3
    assert "tutor/TUTOR.md" in result.stderr


def test_a_missing_rule_fails_and_names_it(contract_repo: Path) -> None:
    policy = contract_repo / "tutor" / "TUTOR.md"
    text = policy.read_text(encoding="utf-8")
    cut = re.sub(r"- \*\*TUTOR-007\*\*.*?\n(?=- \*\*)", "", text, flags=re.S)
    assert cut != text
    policy.write_text(cut, encoding="utf-8")
    result = check(contract_repo)
    assert result.returncode == 3
    assert "TUTOR-007" in result.stderr


def test_a_duplicate_rule_fails(contract_repo: Path) -> None:
    append(contract_repo / "tutor" / "TUTOR.md", "- **TUTOR-001** Again.\n")
    result = check(contract_repo)
    assert result.returncode == 3
    assert "duplicate" in result.stderr


def test_a_policy_that_names_a_technique_fails(contract_repo: Path) -> None:
    append(contract_repo / "tutor" / "TUTOR.md", "\nTry a hash map for lookups.\n")
    result = check(contract_repo)
    assert result.returncode == 3
    assert "hash map" in result.stderr.lower()


def test_dev_rules_that_import_the_policy_fail(contract_repo: Path) -> None:
    append(contract_repo / "CLAUDE.md", "\n@tutor/TUTOR.md\n")
    result = check(contract_repo)
    assert result.returncode == 3
    assert "import" in result.stderr


def test_a_missing_dev_rules_file_fails(contract_repo: Path) -> None:
    (contract_repo / "CLAUDE.md").unlink()
    result = check(contract_repo)
    assert result.returncode == 3
    assert "CLAUDE.md" in result.stderr


def test_a_cursor_rule_that_always_applies_fails(contract_repo: Path) -> None:
    rule = contract_repo / ".cursor" / "rules" / "practice-tutor.mdc"
    text = rule.read_text(encoding="utf-8")
    assert "alwaysApply: false" in text
    rule.write_text(text.replace("alwaysApply: false", "alwaysApply: true"), "utf-8")
    result = check(contract_repo)
    assert result.returncode == 3
    assert "alwaysApply" in result.stderr


def test_the_contract_passes_without_any_cursor_files(contract_repo: Path) -> None:
    shutil.rmtree(contract_repo / ".cursor")
    assert check(contract_repo).returncode == 0


def test_an_unignored_practice_directory_fails(contract_repo: Path) -> None:
    (contract_repo / ".gitignore").write_text("__pycache__/\n", encoding="utf-8")
    result = check(contract_repo)
    assert result.returncode == 3
    assert ".practice" in result.stderr


def test_every_problem_is_reported_in_one_run(contract_repo: Path) -> None:
    (contract_repo / ".gitignore").write_text("", encoding="utf-8")
    (contract_repo / "CLAUDE.md").unlink()
    result = check(contract_repo)
    assert result.returncode == 3
    assert ".practice" in result.stderr and "CLAUDE.md" in result.stderr


def test_classes_command_prints_the_vocabulary_block() -> None:
    result = run_practice("tutor", "classes")
    assert result.returncode == 0
    assert "- `reference_solution`: spoiler" in result.stdout
    assert "- `statement_summary`: open" in result.stdout


def test_start_without_history_shows_defaults_and_creates_nothing(
    tmp_path: Path,
) -> None:
    practice_dir = tmp_path / "practice"
    result = run_practice("tutor", "start", practice_dir=practice_dir)
    assert result.returncode == 0, result.stderr
    assert "tutor/TUTOR.md" in result.stdout
    assert "Mode: practice" in result.stdout
    assert "Timing: untimed" in result.stdout
    assert "No unfinished attempt" in result.stdout
    assert not practice_dir.exists()


def start_attempt(practice_dir: Path, package: Path, *extra: str) -> str:
    result = run_practice(
        "attempt",
        "start",
        "leetcode",
        "1",
        "--package",
        str(package),
        *extra,
        practice_dir=practice_dir,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    match = re.search(r"Started attempt (\S+)", result.stdout)
    assert match is not None
    return match.group(1)


def test_start_reports_the_active_attempt_without_leaking_private_text(
    tmp_path: Path, leetcode_two_sum_package: Path
) -> None:
    practice_dir = tmp_path / "practice"
    attempt_id = start_attempt(
        practice_dir, leetcode_two_sum_package, "--mode", "study"
    )
    code = practice_dir / "attempts" / "leetcode-1" / attempt_id / "solution.py"
    code.write_text("SECRET_APPROACH_MARKER = 1\n", encoding="utf-8")
    noted = run_practice(
        "attempt",
        "note-assistance",
        attempt_id,
        "--kind",
        "hint",
        "--level",
        "1",
        "--summary",
        "SECRET_SUMMARY_MARKER",
        practice_dir=practice_dir,
    )
    assert noted.returncode == 0, noted.stderr

    result = run_practice("tutor", "start", practice_dir=practice_dir)

    assert result.returncode == 0, result.stderr
    assert attempt_id in result.stdout
    assert "Mode: study" in result.stdout
    assert "Timing: untimed" in result.stdout
    assert "Assistance recorded: 1 event, highest hint level 1" in result.stdout
    assert "SECRET" not in result.stdout + result.stderr


def test_timed_is_reported_only_when_the_attempt_chose_it(
    tmp_path: Path, leetcode_two_sum_package: Path
) -> None:
    practice_dir = tmp_path / "practice"
    start_attempt(practice_dir, leetcode_two_sum_package, "--timed")
    result = run_practice("tutor", "start", practice_dir=practice_dir)
    assert "Timing: timed (chosen when the attempt started)" in result.stdout
