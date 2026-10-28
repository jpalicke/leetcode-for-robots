# ABOUTME: Integration tests that run real solutions in real child processes.
# ABOUTME: Covers every honest outcome, evidence hashes and process tree cleanup.

import hashlib
import os
import subprocess
import sys
import time
from collections.abc import Callable
from datetime import datetime
from pathlib import Path
from typing import Any

import pytest

from practice.package import ExercisePackage, load_package
from practice.runner import RunResult, run_exercise

Solution = Callable[[str], Path]
MakePackage = Callable[..., Path]

DOUBLE: dict[str, Any] = {
    "platform": "fixture",
    "id": "double",
    "title": "Double",
    "language": "python",
    "callable": {"adapter": "function", "name": "double", "parameters": ["x"]},
}
DOUBLE_SUITE: dict[str, Any] = {
    "version": "1",
    "cases": [
        {"id": "two", "args": [2], "expected": 4},
        {"id": "zero", "args": [0], "expected": 0},
    ],
}


def run_two_sum(package_dir: Path, solution: Path, timeout: float = 30.0) -> RunResult:
    return run_exercise(load_package(package_dir), solution, timeout=timeout)


def write_solution(tmp_path: Path, source: str) -> Path:
    path = tmp_path / "solution.py"
    path.write_text(source, encoding="utf-8")
    return path


def statuses(result: RunResult) -> list[str]:
    return [case.outcome for case in result.cases]


def process_is_running(pid: int) -> bool:
    if sys.platform == "win32":
        listing = subprocess.run(
            ["tasklist", "/FI", f"PID eq {pid}", "/NH", "/FO", "CSV"],
            capture_output=True,
            text=True,
            check=False,
        )
        return f'"{pid}"' in listing.stdout
    else:
        try:
            os.kill(pid, 0)  # Signal 0 only checks existence; POSIX only.
        except ProcessLookupError:
            return False
        return True


@pytest.mark.parametrize(
    "name", ["correct_hash_map", "correct_brute_force", "noisy_correct"]
)
def test_alternate_valid_algorithms_pass(
    two_sum_package: Path, two_sum_solution: Solution, name: str
) -> None:
    result = run_two_sum(two_sum_package, two_sum_solution(name))

    assert result.status == "passed", result.message
    assert statuses(result) == ["passed"] * 5


def test_wrong_answer_fails_with_case_id_expected_and_actual(
    two_sum_package: Path, two_sum_solution: Solution
) -> None:
    result = run_two_sum(two_sum_package, two_sum_solution("wrong_answer"))

    assert result.status == "failed"
    by_id = {case.case_id: case for case in result.cases}
    assert by_id["example-1"].outcome == "passed"
    failure = by_id["example-2"]
    assert failure.outcome == "failed"
    assert failure.actual == [0, 1]
    assert failure.expected == [1, 2]
    assert "example-2" in result.message or "failed" in result.message


@pytest.mark.parametrize("name", ["stub_pass", "stub_not_implemented"])
def test_stubs_are_incomplete_and_never_run(
    two_sum_package: Path, two_sum_solution: Solution, name: str
) -> None:
    result = run_two_sum(two_sum_package, two_sum_solution(name))

    assert result.status == "stub"
    assert statuses(result) == ["not_run"] * 5
    assert "incomplete" in result.message


def test_runtime_exception_is_an_error_with_the_exception_named(
    two_sum_package: Path, two_sum_solution: Solution
) -> None:
    result = run_two_sum(two_sum_package, two_sum_solution("raises_error"))

    assert result.status == "error"
    assert statuses(result) == ["error"] * 5
    assert "IndexError" in result.cases[0].detail


def test_unserializable_return_value_is_malformed_output(
    two_sum_package: Path, two_sum_solution: Solution
) -> None:
    result = run_two_sum(two_sum_package, two_sum_solution("malformed_output"))

    assert result.status == "malformed"
    assert statuses(result) == ["malformed"] * 5


def test_import_error_is_an_error_in_the_import_phase(
    two_sum_package: Path, two_sum_solution: Solution
) -> None:
    result = run_two_sum(two_sum_package, two_sum_solution("import_error"))

    assert result.status == "error"
    assert "import" in result.message
    assert "ModuleNotFoundError" in result.message
    assert statuses(result) == ["not_run"] * 5


def test_syntax_error_is_an_import_phase_error(
    two_sum_package: Path, tmp_path: Path
) -> None:
    solution = write_solution(tmp_path, "def two_sum(nums, target)\n    return []\n")

    result = run_two_sum(two_sum_package, solution)

    assert result.status == "error"
    assert "SyntaxError" in result.message


def test_missing_function_is_an_error(two_sum_package: Path, tmp_path: Path) -> None:
    solution = write_solution(tmp_path, "def other(nums, target):\n    return []\n")

    result = run_two_sum(two_sum_package, solution)

    assert result.status == "error"
    assert "two_sum" in result.message


def test_none_return_without_a_stub_body_is_malformed_when_forbidden(
    two_sum_package: Path, tmp_path: Path
) -> None:
    solution = write_solution(tmp_path, "def two_sum(nums, target):\n    nums.sort()\n")

    result = run_two_sum(two_sum_package, solution)

    assert result.status == "malformed"
    assert "None" in result.cases[0].detail


def test_infinite_loop_times_out_and_is_not_a_pass(
    two_sum_package: Path, two_sum_solution: Solution
) -> None:
    started = time.monotonic()
    result = run_two_sum(
        two_sum_package, two_sum_solution("infinite_loop"), timeout=1.5
    )

    assert result.status == "timeout"
    assert time.monotonic() - started < 15
    assert result.cases[0].outcome == "timeout"
    assert statuses(result)[1:] == ["not_run"] * 4
    assert any("asymptotic" in note for note in result.notes)


def test_timeout_keeps_results_of_cases_that_finished_first(
    make_package: MakePackage, tmp_path: Path
) -> None:
    source = "def double(x):\n    while x == 0:\n        pass\n    return x * 2\n"

    result = run_exercise(
        load_package(make_package(DOUBLE, DOUBLE_SUITE)),
        write_solution(tmp_path, source),
        timeout=1.5,
    )

    assert result.status == "timeout"
    assert statuses(result) == ["passed", "timeout"]


def test_timeout_kills_the_whole_process_tree(
    two_sum_package: Path, tmp_path: Path
) -> None:
    pid_file = tmp_path / "grandchild.pid"
    source = (
        "import subprocess, sys\n"
        "from pathlib import Path\n"
        "\n"
        "def two_sum(nums, target):\n"
        "    child = subprocess.Popen(\n"
        "        [sys.executable, '-c', 'import time; time.sleep(600)']\n"
        "    )\n"
        f"    Path({str(pid_file)!r}).write_text(str(child.pid))\n"
        "    while True:\n"
        "        pass\n"
    )

    result = run_two_sum(two_sum_package, write_solution(tmp_path, source), timeout=3)

    assert result.status == "timeout"
    grandchild = int(pid_file.read_text())
    deadline = time.monotonic() + 10
    while process_is_running(grandchild) and time.monotonic() < deadline:
        time.sleep(0.2)
    assert not process_is_running(grandchild)


def test_evidence_binds_the_code_and_suite_hashes_and_a_timestamp(
    two_sum_package: Path, two_sum_solution: Solution
) -> None:
    solution = two_sum_solution("correct_hash_map")
    package = load_package(two_sum_package)

    result = run_exercise(package, solution, timeout=30)

    assert result.code_sha256 == hashlib.sha256(solution.read_bytes()).hexdigest()
    assert result.suite_sha256 == package.suite_sha256
    assert result.suite_version == "fixture-1"
    assert datetime.fromisoformat(result.run_at).tzinfo is not None
    assert (result.platform, result.problem_id) == (
        "fixture",
        "two-sum-runner-fixture",
    )
    assert result.timeout_seconds == 30


def test_editing_the_code_changes_the_code_hash(
    two_sum_package: Path, two_sum_solution: Solution, tmp_path: Path
) -> None:
    original = two_sum_solution("correct_hash_map")
    edited = tmp_path / "edited.py"
    edited.write_text(original.read_text(encoding="utf-8") + "\n# edit\n")

    before = run_two_sum(two_sum_package, original)
    after = run_two_sum(two_sum_package, edited)

    assert before.code_sha256 != after.code_sha256
    assert before.suite_sha256 == after.suite_sha256


def test_result_converts_to_json_ready_data(
    two_sum_package: Path, two_sum_solution: Solution
) -> None:
    result = run_two_sum(two_sum_package, two_sum_solution("wrong_answer"))

    data = result.to_dict()

    assert data["status"] == "failed"
    assert data["code_sha256"] == result.code_sha256
    assert data["cases"][1]["case_id"] == "example-2"
    assert data["cases"][1]["actual"] == [0, 1]


def test_missing_suite_is_never_a_pass(
    make_package: MakePackage, tmp_path: Path
) -> None:
    solution = write_solution(tmp_path, "def double(x):\n    return x * 2\n")

    result = run_exercise(load_package(make_package(DOUBLE, None)), solution)

    assert result.status == "no_suite"
    assert result.suite_sha256 is None


def test_empty_suite_is_never_a_pass(make_package: MakePackage, tmp_path: Path) -> None:
    solution = write_solution(tmp_path, "def double(x):\n    return x * 2\n")
    package = load_package(make_package(DOUBLE, {"version": "1", "cases": []}))

    result = run_exercise(package, solution)

    assert result.status == "no_suite"
    assert result.suite_sha256 is not None


@pytest.mark.parametrize(
    "change",
    [
        {"callable": {"adapter": "class", "name": "Solution", "parameters": ["x"]}},
        {"language": "rust"},
        {"checker": "no_such_checker"},
    ],
)
def test_unsupported_contracts_are_reported_not_run(
    make_package: MakePackage, tmp_path: Path, change: dict[str, Any]
) -> None:
    solution = write_solution(tmp_path, "def double(x):\n    return x * 2\n")
    package = load_package(make_package({**DOUBLE, **change}, DOUBLE_SUITE))

    result = run_exercise(package, solution)

    assert result.status == "unsupported"
    assert statuses(result) == ["not_run"] * 2


def test_each_case_gets_freshly_deserialized_arguments(
    make_package: MakePackage, tmp_path: Path
) -> None:
    metadata = {
        **DOUBLE,
        "callable": {"adapter": "function", "name": "grow", "parameters": ["items"]},
    }
    same_args = [[1, 2, 3]]
    suite = {
        "version": "1",
        "cases": [
            {"id": "first", "args": same_args, "expected": 4},
            {"id": "second", "args": same_args, "expected": 4},
        ],
    }
    solution = write_solution(
        tmp_path, "def grow(items):\n    items.append(0)\n    return len(items)\n"
    )

    result = run_exercise(load_package(make_package(metadata, suite)), solution)

    assert result.status == "passed", result.message


def test_none_is_a_valid_answer_only_when_the_contract_allows_it(
    make_package: MakePackage, tmp_path: Path
) -> None:
    metadata = {**DOUBLE, "allow_none": True}
    suite = {
        "version": "1",
        "cases": [{"id": "nothing", "args": [1], "expected": None}],
    }
    solution = write_solution(tmp_path, "def double(x):\n    return None\n")

    result = run_exercise(load_package(make_package(metadata, suite)), solution)

    assert result.status == "passed", result.message


def test_loaded_package_type_is_exposed(two_sum_package: Path) -> None:
    assert isinstance(load_package(two_sum_package), ExercisePackage)
