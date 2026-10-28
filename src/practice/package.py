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

    suite = None
    suite_sha256 = None
    if suite_data is not None:
        suite = _parse_suite(suite_data, len(parameters), checker)
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
