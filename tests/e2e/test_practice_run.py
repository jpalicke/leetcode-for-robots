# ABOUTME: End-to-end tests that run the practice run command in a subprocess.
# ABOUTME: Shows four honest outcomes for the Two Sum fixture and the exit codes.

import hashlib
import json
import subprocess
import sys
from collections.abc import Callable
from pathlib import Path

import pytest

Solution = Callable[[str], Path]


def run_practice(
    *args: str, cwd: Path | None = None
) -> subprocess.CompletedProcess[str]:
    scripts = Path(sys.executable).parent
    command = next(
        path
        for name in ("practice.exe", "practice")
        if (path := scripts / name).exists()
    )
    return subprocess.run(
        [str(command), *args],
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=120,
        check=False,
        cwd=cwd,
    )


@pytest.mark.parametrize(
    ("solution", "word", "code"),
    [
        ("correct_hash_map", "PASSED", 0),
        ("wrong_answer", "FAILED", 1),
        ("stub_pass", "STUB", 1),
        ("infinite_loop", "TIMEOUT", 1),
    ],
)
def test_demo_four_solutions_give_four_honest_outcomes(
    two_sum_package: Path,
    two_sum_solution: Solution,
    solution: str,
    word: str,
    code: int,
) -> None:
    result = run_practice(
        "run", str(two_sum_package), str(two_sum_solution(solution)), "--timeout", "2"
    )

    assert result.returncode == code, result.stdout + result.stderr
    assert result.stdout.startswith(word)
    assert result.stderr == ""
    assert "Traceback" not in result.stdout


def test_failure_report_names_the_case_expected_and_actual(
    two_sum_package: Path, two_sum_solution: Solution
) -> None:
    result = run_practice(
        "run", str(two_sum_package), str(two_sum_solution("wrong_answer"))
    )

    assert "example-2" in result.stdout
    assert "expected" in result.stdout
    assert "[0, 1]" in result.stdout


def test_timeout_report_warns_it_proves_nothing_about_complexity(
    two_sum_package: Path, two_sum_solution: Solution
) -> None:
    result = run_practice(
        "run",
        str(two_sum_package),
        str(two_sum_solution("infinite_loop")),
        "--timeout",
        "1.5",
    )

    assert "asymptotic" in result.stdout


def test_json_output_carries_evidence(
    two_sum_package: Path, two_sum_solution: Solution
) -> None:
    solution = two_sum_solution("correct_brute_force")

    result = run_practice("run", str(two_sum_package), str(solution), "--json")

    assert result.returncode == 0, result.stdout + result.stderr
    data = json.loads(result.stdout)
    assert data["status"] == "passed"
    assert data["code_sha256"] == hashlib.sha256(solution.read_bytes()).hexdigest()
    assert len(data["suite_sha256"]) == 64
    assert len(data["cases"]) == 5
    assert data["run_at"]


def test_running_never_writes_learner_history(
    two_sum_package: Path, two_sum_solution: Solution, tmp_path: Path
) -> None:
    run_practice(
        "run",
        str(two_sum_package),
        str(two_sum_solution("correct_hash_map")),
        cwd=tmp_path,
    )

    assert list(tmp_path.iterdir()) == []


def test_missing_solution_file_is_a_usage_error(
    two_sum_package: Path, tmp_path: Path
) -> None:
    result = run_practice("run", str(two_sum_package), str(tmp_path / "nope.py"))

    assert result.returncode == 2
    assert result.stdout == ""
    assert "nope.py" in result.stderr
    assert "Traceback" not in result.stderr


def test_bad_timeout_is_a_usage_error(
    two_sum_package: Path, two_sum_solution: Solution
) -> None:
    result = run_practice(
        "run",
        str(two_sum_package),
        str(two_sum_solution("correct_hash_map")),
        "--timeout",
        "0",
    )

    assert result.returncode == 2
    assert "timeout" in result.stderr


def test_invalid_package_exits_3_with_a_reason(
    two_sum_solution: Solution, tmp_path: Path
) -> None:
    (tmp_path / "problem.json").write_text("{broken", encoding="utf-8")

    result = run_practice(
        "run", str(tmp_path), str(two_sum_solution("correct_hash_map"))
    )

    assert result.returncode == 3
    assert result.stdout == ""
    assert "not valid JSON" in result.stderr
    assert "Traceback" not in result.stderr


def test_missing_suite_is_reported_and_exits_1(
    two_sum_package: Path, two_sum_solution: Solution, tmp_path: Path
) -> None:
    (tmp_path / "problem.json").write_bytes(
        (two_sum_package / "problem.json").read_bytes()
    )

    result = run_practice(
        "run", str(tmp_path), str(two_sum_solution("correct_hash_map"))
    )

    assert result.returncode == 1
    assert result.stdout.startswith("NO_SUITE")


def test_search_still_works_alongside_run() -> None:
    result = run_practice("search", "two sum")

    assert result.returncode == 0
    assert "Two Sum" in result.stdout
