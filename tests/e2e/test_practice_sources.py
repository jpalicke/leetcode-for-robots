# ABOUTME: End-to-end tests that run `practice sources` in a subprocess, real server.
# ABOUTME: Covers add, verify, show, list, add-local, tampering and failure exit codes.

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from conftest import UpstreamServer

REVISION = "0123456789abcdef0123456789abcdef01234567"
SOURCE_PATH = "python/0001-two-sum.py"
SOURCE_ID = "sample-two-sum"
SOURCE_BYTES = b"def two_sum(nums, target):\r\n    return []"
LICENSE_BYTES = b"MIT License\r\n\r\nCopyright (c) Example Authors\r\n"


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


def add_args(server: UpstreamServer, references: Path, **overrides: str) -> list[str]:
    fields = {
        "--repository": "https://github.com/example/sample",
        "--revision": REVISION,
        "--path": SOURCE_PATH,
        "--license-path": "LICENSE",
        "--license-id": "MIT",
        "--terms": "Keep the copyright and permission notice with copies.",
        "--classification": "reference_solution",
        "--title": "Sample: Two Sum (Python)",
        "--raw-base": server.base_url,
        "--actor": "pytest",
    }
    fields.update(overrides)
    flat = [part for pair in fields.items() for part in pair]
    return ["--references", str(references), "sources", "add", SOURCE_ID, *flat]


@pytest.fixture
def references(tmp_path: Path) -> Path:
    return tmp_path / "references"


@pytest.fixture
def imported(upstream_server: UpstreamServer, references: Path) -> Path:
    upstream_server.publish(REVISION, SOURCE_PATH, SOURCE_BYTES)
    upstream_server.publish(REVISION, "LICENSE", LICENSE_BYTES)
    result = run_practice(*add_args(upstream_server, references))
    assert result.returncode == 0, result.stderr
    return references


def test_add_preserves_exact_bytes_and_leaves_evidence_unclaimed(
    imported: Path,
) -> None:
    folder = imported / "upstream" / SOURCE_ID
    assert (folder / "0001-two-sum.py").read_bytes() == SOURCE_BYTES
    assert (folder / "LICENSE").read_bytes() == LICENSE_BYTES
    manifest = json.loads((imported / "manifests" / f"{SOURCE_ID}.json").read_text())
    assert manifest["evidence"]["local_validation"]["status"] == "none"
    assert manifest["evidence"]["platform_acceptance"]["status"] == "none"


def test_add_prints_the_sha256_of_what_it_kept(
    upstream_server: UpstreamServer, references: Path
) -> None:
    upstream_server.publish(REVISION, SOURCE_PATH, SOURCE_BYTES)
    upstream_server.publish(REVISION, "LICENSE", LICENSE_BYTES)
    result = run_practice(*add_args(upstream_server, references))
    assert result.returncode == 0
    assert f"preserved {SOURCE_ID}" in result.stdout
    assert "sha256" in result.stdout
    assert "validation: none" in result.stdout


def test_verify_passes_for_an_untouched_import(imported: Path) -> None:
    result = run_practice("--references", str(imported), "sources", "verify")
    assert result.returncode == 0, result.stderr
    assert f"ok  {SOURCE_ID}" in result.stdout
    assert result.stderr == ""


def test_verify_fails_with_exit_3_after_tampering(imported: Path) -> None:
    stored = imported / "upstream" / SOURCE_ID / "0001-two-sum.py"
    stored.write_bytes(SOURCE_BYTES + b"\r\n# edited\r\n")
    result = run_practice("--references", str(imported), "sources", "verify")
    assert result.returncode == 3
    assert "sha256 mismatch" in result.stderr
    assert "0001-two-sum.py" in result.stderr


def test_verify_fails_when_the_notice_is_removed(imported: Path) -> None:
    (imported / "upstream" / SOURCE_ID / "LICENSE").unlink()
    result = run_practice("--references", str(imported), "sources", "verify")
    assert result.returncode == 3
    assert "LICENSE: file is missing" in result.stderr


def test_verify_without_a_references_folder_exits_3(tmp_path: Path) -> None:
    result = run_practice("--references", str(tmp_path / "nope"), "sources", "verify")
    assert result.returncode == 3
    assert "references folder not found" in result.stderr


def test_show_prints_the_citation(imported: Path) -> None:
    result = run_practice("--references", str(imported), "sources", "show", SOURCE_ID)
    assert result.returncode == 0, result.stderr
    assert "classification: reference_solution (spoiler)" in result.stdout
    assert REVISION in result.stdout
    assert "license:        MIT" in result.stdout
    assert "local validation:    none" in result.stdout


def test_show_json_is_a_citation_record(imported: Path) -> None:
    result = run_practice(
        "--references", str(imported), "sources", "show", SOURCE_ID, "--json"
    )
    assert result.returncode == 0, result.stderr
    record = json.loads(result.stdout)
    assert record["id"] == SOURCE_ID
    assert record["revision"] == REVISION
    assert record["license_identifier"] == "MIT"
    assert record["spoiler"] is True
    assert record["local_validation"] == "none"


def test_show_unknown_id_exits_1(imported: Path) -> None:
    result = run_practice("--references", str(imported), "sources", "show", "nope")
    assert result.returncode == 1
    assert "no source with id 'nope'" in result.stderr


def test_show_a_tampered_source_exits_3(imported: Path) -> None:
    stored = imported / "upstream" / SOURCE_ID / "0001-two-sum.py"
    stored.write_bytes(b"changed")
    result = run_practice("--references", str(imported), "sources", "show", SOURCE_ID)
    assert result.returncode == 3
    assert "sha256 mismatch" in result.stderr


def test_list_names_each_source(imported: Path) -> None:
    result = run_practice("--references", str(imported), "sources", "list")
    assert result.returncode == 0
    assert f"{SOURCE_ID}  upstream  reference_solution" in result.stdout


def test_usage_errors_exit_2(references: Path) -> None:
    result = run_practice("--references", str(references), "sources", "add")
    assert result.returncode == 2
    result = run_practice(
        "--references",
        str(references),
        "sources",
        "add",
        "x",
        "--classification",
        "not_a_class",
    )
    assert result.returncode == 2


def test_add_fetch_failure_exits_3_and_writes_nothing(
    upstream_server: UpstreamServer, references: Path
) -> None:
    result = run_practice(*add_args(upstream_server, references))
    assert result.returncode == 3
    assert "HTTP 404" in result.stderr
    assert not references.exists()


def test_add_refuses_a_non_permissive_license_without_a_policy_note(
    upstream_server: UpstreamServer, references: Path
) -> None:
    upstream_server.publish(REVISION, SOURCE_PATH, SOURCE_BYTES)
    upstream_server.publish(REVISION, "LICENSE", LICENSE_BYTES)
    result = run_practice(
        *add_args(upstream_server, references, **{"--license-id": "CC-BY-SA-4.0"})
    )
    assert result.returncode == 3
    assert "policy_note" in result.stderr
    assert not references.exists()


def test_add_refuses_to_overwrite_an_existing_source(
    upstream_server: UpstreamServer, imported: Path
) -> None:
    result = run_practice(*add_args(upstream_server, imported))
    assert result.returncode == 3
    assert "already exists" in result.stderr
    stored = imported / "upstream" / SOURCE_ID / "0001-two-sum.py"
    assert stored.read_bytes() == SOURCE_BYTES


def adapter_args(references: Path, adapter: Path, derived_from: str) -> tuple[str, ...]:
    return (
        "--references",
        str(references),
        "sources",
        "add-local",
        "sample-adapter",
        "--kind",
        "adaptation",
        "--file",
        str(adapter),
        "--classification",
        "algorithm_implementation",
        "--title",
        "Adapter for the sample",
        "--actor",
        "pytest",
        "--derived-from",
        derived_from,
        "--transformation",
        "Wrapped in the runner entry point.",
    )


def test_add_local_registers_an_adaptation_apart_from_upstream(
    imported: Path, tmp_path: Path
) -> None:
    adapter = tmp_path / "adapter.py"
    adapter.write_text("def two_sum(nums, target):\n    return [0, 1]\n")
    result = run_practice(*adapter_args(imported, adapter, SOURCE_ID))
    assert result.returncode == 0, result.stderr
    assert (imported / "adaptations" / "sample-adapter" / "adapter.py").is_file()
    verified = run_practice("--references", str(imported), "sources", "verify")
    assert verified.returncode == 0, verified.stderr


def test_add_local_adaptation_of_a_missing_upstream_exits_1(
    imported: Path, tmp_path: Path
) -> None:
    adapter = tmp_path / "adapter.py"
    adapter.write_text("x = 1\n")
    result = run_practice(*adapter_args(imported, adapter, "missing-upstream"))
    assert result.returncode == 1
    assert "missing-upstream" in result.stderr
