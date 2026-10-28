# ABOUTME: Unit tests for loading, validating and hashing exercise packages.
# ABOUTME: Uses the Two Sum fixture package and small throwaway packages on disk.

import json
from collections.abc import Callable
from pathlib import Path
from typing import Any

import pytest

from practice.package import PackageError, load_package

METADATA: dict[str, Any] = {
    "platform": "fixture",
    "id": "double",
    "title": "Double",
    "language": "python",
    "callable": {"adapter": "function", "name": "double", "parameters": ["x"]},
}
SUITE: dict[str, Any] = {
    "version": "1",
    "cases": [{"id": "two", "args": [2], "expected": 4}],
}
MakePackage = Callable[..., Path]


def test_fixture_package_loads_with_its_contract(two_sum_package: Path) -> None:
    package = load_package(two_sum_package)

    assert package.platform == "fixture"
    assert package.problem_id == "two-sum-runner-fixture"
    assert package.function_name == "two_sum"
    assert package.parameters == ("nums", "target")
    assert package.checker == "indices_sum_to_target"
    assert package.allow_none is False
    assert package.suite is not None
    assert [case.case_id for case in package.suite.cases][:2] == [
        "example-1",
        "example-2",
    ]


def test_defaults_are_exact_checker_and_none_forbidden(
    make_package: MakePackage,
) -> None:
    package = load_package(make_package(METADATA, SUITE))

    assert package.checker == "exact"
    assert package.allow_none is False


def test_suite_hash_is_stable_and_changes_with_cases_or_metadata(
    tmp_path: Path,
) -> None:
    def hash_for(name: str, metadata: dict[str, Any], suite: dict[str, Any]) -> str:
        folder = tmp_path / name
        folder.mkdir()
        (folder / "problem.json").write_text(json.dumps(metadata), encoding="utf-8")
        (folder / "tests.json").write_text(
            json.dumps(suite, indent=4), encoding="utf-8"
        )
        digest = load_package(folder).suite_sha256
        assert digest is not None
        return digest

    base = hash_for("a", METADATA, SUITE)
    assert len(base) == 64
    assert hash_for("b", METADATA, SUITE) == base
    changed_case = {**SUITE, "cases": [{"id": "two", "args": [2], "expected": 5}]}
    assert hash_for("c", METADATA, changed_case) != base
    changed_metadata = {**METADATA, "title": "Other"}
    assert hash_for("d", changed_metadata, SUITE) != base


def test_missing_suite_file_loads_with_no_suite(make_package: MakePackage) -> None:
    package = load_package(make_package(METADATA, None))

    assert package.suite is None
    assert package.suite_sha256 is None


def test_empty_case_list_loads_as_an_empty_suite(make_package: MakePackage) -> None:
    package = load_package(make_package(METADATA, {"version": "1", "cases": []}))

    assert package.suite is not None
    assert package.suite.cases == ()
    assert package.suite_sha256 is not None


def test_missing_directory_or_metadata_is_an_error(tmp_path: Path) -> None:
    with pytest.raises(PackageError, match="not a directory"):
        load_package(tmp_path / "nope")
    with pytest.raises(PackageError, match=r"problem\.json"):
        load_package(tmp_path)


def test_invalid_json_is_an_error(tmp_path: Path) -> None:
    (tmp_path / "problem.json").write_text("{not json", encoding="utf-8")

    with pytest.raises(PackageError, match="not valid JSON"):
        load_package(tmp_path)


@pytest.mark.parametrize(
    ("change", "message"),
    [
        ({"platform": None}, "platform"),
        ({"id": ""}, "id"),
        ({"language": None}, "language"),
        ({"callable": {"adapter": "function", "name": "f"}}, "parameters"),
        ({"callable": "double"}, "callable"),
        ({"checker": 7}, "checker"),
        ({"allow_none": "no"}, "allow_none"),
    ],
)
def test_invalid_metadata_is_an_error(
    make_package: MakePackage, change: dict[str, Any], message: str
) -> None:
    metadata = {**METADATA, **change}

    with pytest.raises(PackageError, match=message):
        load_package(make_package(metadata, SUITE))


@pytest.mark.parametrize(
    ("suite", "message"),
    [
        ({"cases": []}, "version"),
        ({"version": "1", "cases": {}}, "cases"),
        ({"version": "1", "cases": [{"args": [2], "expected": 4}]}, "id"),
        ({"version": "1", "cases": [{"id": "a", "args": 2, "expected": 4}]}, "args"),
        ({"version": "1", "cases": [{"id": "a", "args": [], "expected": 4}]}, "args"),
        ({"version": "1", "cases": [{"id": "a", "args": [2]}]}, "expected"),
        (
            {
                "version": "1",
                "cases": [
                    {"id": "a", "args": [2], "expected": 4},
                    {"id": "a", "args": [3], "expected": 6},
                ],
            },
            "duplicate",
        ),
    ],
)
def test_invalid_suite_is_an_error(
    make_package: MakePackage, suite: dict[str, Any], message: str
) -> None:
    with pytest.raises(PackageError, match=message):
        load_package(make_package(METADATA, suite))
