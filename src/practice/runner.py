# ABOUTME: Runs a solution file against an exercise package, reporting honest outcomes.
# ABOUTME: Only a non-empty suite with every case passing is ever reported as passed.

import hashlib
import json
import time
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Literal

from practice.checkers import CHECKERS, Checker
from practice.child import ChildReport, run_worker
from practice.package import Case, ExercisePackage
from practice.stubs import is_stub

Status = Literal[
    "passed",
    "failed",
    "error",
    "malformed",
    "timeout",
    "stub",
    "unsupported",
    "no_suite",
]
CaseOutcome = Literal["passed", "failed", "error", "malformed", "timeout", "not_run"]

TIMEOUT_NOTE = (
    "A timeout shows the run did not finish in time. It does not prove "
    "anything about asymptotic complexity."
)


@dataclass
class CaseResult:
    case_id: str
    outcome: CaseOutcome
    detail: str = ""
    expected: Any = None  # For predicate checkers, one example of a valid answer.
    actual: Any = None


@dataclass
class RunResult:
    status: Status
    message: str
    platform: str
    problem_id: str
    suite_version: str | None
    code_sha256: str
    suite_sha256: str | None
    run_at: str
    duration_seconds: float
    timeout_seconds: float
    cases: list[CaseResult] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def run_exercise(
    package: ExercisePackage, solution: Path, timeout: float = 10.0
) -> RunResult:
    """Run the solution against the package. Raises OSError if it cannot be read."""
    code = solution.read_bytes()
    run_at = datetime.now(UTC).isoformat(timespec="seconds")
    started = time.monotonic()
    suite = package.suite
    cases = suite.cases if suite is not None else ()

    def finish(
        status: Status,
        message: str,
        results: list[CaseResult] | None = None,
        notes: list[str] | None = None,
    ) -> RunResult:
        return RunResult(
            status=status,
            message=message,
            platform=package.platform,
            problem_id=package.problem_id,
            suite_version=suite.version if suite is not None else None,
            code_sha256=hashlib.sha256(code).hexdigest(),
            suite_sha256=package.suite_sha256,
            run_at=run_at,
            duration_seconds=round(time.monotonic() - started, 3),
            timeout_seconds=timeout,
            cases=results if results is not None else _not_run(cases),
            notes=notes or [],
        )

    unsupported = _unsupported_reason(package)
    if unsupported:
        return finish("unsupported", f"unsupported: {unsupported}")
    if not cases:
        return finish(
            "no_suite", "the package has no test cases, so nothing was checked"
        )
    source = code.decode("utf-8", errors="replace")
    if is_stub(source, package.function_name, allow_none=package.allow_none):
        return finish(
            "stub",
            f"incomplete: {package.function_name} is still a stub (no real body yet)",
        )

    payload = {
        "function": package.function_name,
        "cases": [
            {"id": case.case_id, "args_json": json.dumps(case.args)} for case in cases
        ],
    }
    report = run_worker(solution, payload, timeout)
    load_failure = _load_failure(report)
    if load_failure:
        return finish("error", load_failure)
    results = _judge_cases(package, cases, report)
    status, message = _summarize(report, results)
    return finish(status, message, results, [TIMEOUT_NOTE] if report.timed_out else [])


def _unsupported_reason(package: ExercisePackage) -> str:
    if package.language != "python":
        return f"language {package.language!r} (only python is supported)"
    if package.adapter != "function":
        return f"adapter {package.adapter!r} (only 'function' is supported)"
    if package.checker not in CHECKERS:
        return f"checker {package.checker!r}"
    return ""


def _not_run(cases: tuple[Case, ...]) -> list[CaseResult]:
    return [CaseResult(c.case_id, "not_run", expected=c.expected) for c in cases]


def _load_failure(report: ChildReport) -> str:
    """Explain why the solution could not be loaded, or return an empty string."""
    for event in report.events:
        if event.get("event") == "import_error":
            return (
                f"import phase failed: {event['type']}: {event['message']}\n"
                f"{event['traceback']}"
            )
        if event.get("event") == "missing_callable":
            return f"the solution defines no callable named {event['name']!r}"
    return ""


def _judge_cases(
    package: ExercisePackage, cases: tuple[Case, ...], report: ChildReport
) -> list[CaseResult]:
    checker = CHECKERS[package.checker]
    events_by_case: dict[str, dict[str, Any]] = {}
    last_started = None
    for event in report.events:
        if event.get("event") == "start":
            last_started = event["case"]
        elif "case" in event:
            events_by_case[event["case"]] = event

    judged: list[CaseResult] = []
    for case in cases:
        result = CaseResult(case.case_id, "not_run", expected=case.expected)
        case_event = events_by_case.get(case.case_id)
        if case_event is not None:
            _apply_event(package, checker, case, case_event, result)
        elif case.case_id == last_started:
            if report.timed_out:
                result.outcome = "timeout"
                result.detail = "the run was stopped while this case was executing"
            else:
                result.outcome = "error"
                result.detail = (
                    f"the child process exited (code {report.exit_code}) "
                    "while running this case"
                )
        judged.append(result)
    return judged


def _apply_event(
    package: ExercisePackage,
    checker: Checker,
    case: Case,
    event: dict[str, Any],
    result: CaseResult,
) -> None:
    kind = event["event"]
    if kind == "case_error":
        result.outcome = "error"
        result.detail = f"{event['type']}: {event['message']}\n{event['traceback']}"
    elif kind == "unserializable":
        result.outcome = "malformed"
        result.detail = event["detail"]
    elif kind == "result":
        result.actual = event["value"]
        if result.actual is None and not package.allow_none:
            result.outcome = "malformed"
            result.detail = "returned None, which this exercise does not allow"
            return
        verdict = checker.check(result.actual, case.expected, case.args)
        result.outcome = verdict.kind
        result.detail = verdict.detail


def _summarize(report: ChildReport, results: list[CaseResult]) -> tuple[Status, str]:
    total = len(results)
    counts = {outcome: 0 for outcome in ("passed", "failed", "error", "malformed")}
    for result in results:
        if result.outcome in counts:
            counts[result.outcome] += 1
    tally = ", ".join(f"{n} {outcome}" for outcome, n in counts.items() if n)
    tally = tally or "0 finished"

    if report.timed_out:
        return "timeout", f"timed out; {tally} of {total} cases"
    if counts["error"]:
        return "error", f"{tally} of {total} cases"
    if counts["malformed"]:
        return "malformed", f"{tally} of {total} cases"
    if counts["failed"]:
        return "failed", f"{tally} of {total} cases"
    if counts["passed"] != total:
        return (
            "error",
            f"the child process exited early (code {report.exit_code}); "
            f"{tally} of {total} cases\n{report.stderr_tail}",
        )
    return "passed", f"all {total} cases passed"
