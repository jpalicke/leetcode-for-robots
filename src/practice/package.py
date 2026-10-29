# ABOUTME: Loads an exercise package: JSON metadata naming the callable plus a suite.
# ABOUTME: Validates the shape and hashes metadata and cases together as suite evidence.

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from practice.checkers import CHECKERS

METADATA_FILE = "problem.json"
SUITE_FILE = "tests.json"


class PackageError(Exception):
    """The package directory cannot be read or fails validation."""


@dataclass(frozen=True)
class Case:
    case_id: str
    args: list[Any]
    expected: Any  # None when the checker works from the arguments alone.


@dataclass(frozen=True)
class ProbeBudget:
    """How many entries of one list argument a solution may look at, by input size.

    growth "log2" allows the bit length of the size (the most a binary search can
    read) plus slack, so a search that also checks both ends still fits.
    """

    argument: str
    argument_index: int
    growth: str
    slack: int

    def limit(self, length: int) -> int:
        return length.bit_length() + self.slack


@dataclass(frozen=True)
class Suite:
    version: str
    cases: tuple[Case, ...]


@dataclass(frozen=True)
class ExercisePackage:
    path: Path
    platform: str
    problem_id: str
    title: str
    language: str
    adapter: str
    function_name: str
    parameters: tuple[str, ...]
    checker: str
    allow_none: bool
    suite: Suite | None  # None when the package has no test suite file.
    suite_sha256: str | None
    probe_budget: ProbeBudget | None = None  # None: the package sets no limit.


def load_package(directory: Path) -> ExercisePackage:
    if not directory.is_dir():
        raise PackageError(f"{directory} is not a directory")
    metadata = _read_json(directory / METADATA_FILE)
    suite_path = directory / SUITE_FILE
    suite_data = _read_json(suite_path) if suite_path.exists() else None

    callable_data = _field(metadata, "callable", dict)
    checker = metadata.get("checker", "exact")
    if not isinstance(checker, str):
        raise PackageError("checker must be a string naming an output checker")
    allow_none = metadata.get("allow_none", False)
    if not isinstance(allow_none, bool):
        raise PackageError("allow_none must be true or false")
    parameters = _field(callable_data, "parameters", list, "callable parameters")
    if not all(isinstance(name, str) and name for name in parameters):
        raise PackageError("callable parameters must be non-empty strings")

    probe_budget = _parse_probe_budget(metadata.get("probe_budget"), parameters)
    suite = None
    suite_sha256 = None
    if suite_data is not None:
        suite = _parse_suite(suite_data, len(parameters), checker)
        if probe_budget is not None:
            _require_lists(suite, probe_budget)
        suite_sha256 = _hash_suite(metadata, suite_data)
    return ExercisePackage(
        path=directory,
        platform=_field(metadata, "platform", str),
        problem_id=_field(metadata, "id", str),
        title=str(metadata.get("title", "")),
        language=_field(metadata, "language", str),
        adapter=_field(callable_data, "adapter", str, "callable adapter"),
        function_name=_field(callable_data, "name", str, "callable name"),
        parameters=tuple(parameters),
        checker=checker,
        allow_none=allow_none,
        suite=suite,
        suite_sha256=suite_sha256,
        probe_budget=probe_budget,
    )


PROBE_BUDGET_KEYS = {"argument", "growth", "slack"}
DEFAULT_PROBE_SLACK = 2


def _parse_probe_budget(raw: object, parameters: list[str]) -> ProbeBudget | None:
    if raw is None:
        return None
    if not isinstance(raw, dict):
        raise PackageError("probe_budget must be an object")
    unknown = sorted(set(raw) - PROBE_BUDGET_KEYS)
    if unknown:
        raise PackageError(f"probe_budget has unknown keys: {', '.join(unknown)}")
    argument = raw.get("argument")
    if not isinstance(argument, str) or not argument:
        raise PackageError("probe_budget argument must name a parameter")
    if argument not in parameters:
        raise PackageError(f"probe_budget argument {argument!r} is not a parameter")
    if raw.get("growth") != "log2":
        raise PackageError('probe_budget growth must be "log2"')
    slack = raw.get("slack", DEFAULT_PROBE_SLACK)
    if isinstance(slack, bool) or not isinstance(slack, int) or slack < 0:
        raise PackageError("probe_budget slack must be a whole number, zero or more")
    return ProbeBudget(argument, parameters.index(argument), "log2", slack)


def _require_lists(suite: Suite, budget: ProbeBudget) -> None:
    """A probe budget counts reads of a list, so every case must pass one."""
    for case in suite.cases:
        if not isinstance(case.args[budget.argument_index], list):
            raise PackageError(
                f"case {case.case_id!r}: {budget.argument} must be a list "
                "because the package sets a probe_budget"
            )


def _read_json(path: Path) -> dict[str, Any]:
    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as error:
        raise PackageError(f"cannot read {path}: {error}") from error
    try:
        data = json.loads(text, parse_constant=_reject_constant)
    except (json.JSONDecodeError, ValueError) as error:
        raise PackageError(f"{path} is not valid JSON: {error}") from error
    if not isinstance(data, dict):
        raise PackageError(f"{path} must hold a JSON object")
    return data


def _reject_constant(name: str) -> object:
    raise ValueError(f"{name} is not allowed in exercise files")


def _field(data: dict[str, Any], key: str, kind: type, label: str = "") -> Any:
    value = data.get(key)
    if not isinstance(value, kind) or (isinstance(value, str) and not value):
        article = "a non-empty string" if kind is str else f"a {kind.__name__}"
        raise PackageError(f"{label or key} must be {article}")
    return value


def _parse_suite(data: dict[str, Any], parameter_count: int, checker: str) -> Suite:
    version = _field(data, "version", str, "suite version")
    raw_cases = _field(data, "cases", list)
    known = CHECKERS.get(checker)  # An unknown checker is reported at run time.
    cases: list[Case] = []
    seen: set[str] = set()
    for index, raw in enumerate(raw_cases):
        if not isinstance(raw, dict):
            raise PackageError(f"case {index} must be a JSON object")
        case_id = raw.get("id")
        if not isinstance(case_id, str) or not case_id:
            raise PackageError(f"case {index}: id must be a non-empty string")
        if case_id in seen:
            raise PackageError(f"duplicate case id {case_id!r}")
        seen.add(case_id)
        args = raw.get("args")
        if not isinstance(args, list) or len(args) != parameter_count:
            raise PackageError(
                f"case {case_id!r}: args must be a list of {parameter_count} values"
            )
        if known is not None and known.expects != "none":
            if "expected" not in raw:
                raise PackageError(f"case {case_id!r}: expected is required")
            if known.expects == "list" and not isinstance(raw["expected"], list):
                raise PackageError(f"case {case_id!r}: expected must be a list")
        cases.append(Case(case_id, args, raw.get("expected")))
    return Suite(version, tuple(cases))


def _hash_suite(metadata: dict[str, Any], suite_data: dict[str, Any]) -> str:
    """Hash parsed content so formatting changes do not alter the evidence."""
    canonical = json.dumps(
        {"metadata": metadata, "suite": suite_data},
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
    )
    return hashlib.sha256(canonical.encode("ascii")).hexdigest()
