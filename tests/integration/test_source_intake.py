# ABOUTME: Integration tests for source intake, verification, citations and evidence.
# ABOUTME: Real files and a real local HTTP server; nothing is mocked or executed blind.

from __future__ import annotations

import json
from collections.abc import Callable
from datetime import UTC, datetime
from importlib.metadata import version
from pathlib import Path
from typing import TYPE_CHECKING, Any

import pytest

from practice.classification import is_spoiler
from practice.package import load_package
from practice.runner import run_exercise
from practice.source_fetch import FetchError, fetch_url
from practice.source_manifest import sha256_hex, validation_state
from practice.sources import (
    LocalRequest,
    SourceError,
    SourceNotFoundError,
    UpstreamRequest,
    add_local,
    add_upstream,
    citation,
    list_source_ids,
    load_manifest,
    record_validation,
    validate_source,
    verify_references,
)

if TYPE_CHECKING:
    from conftest import UpstreamServer

REVISION = "0123456789abcdef0123456789abcdef01234567"
SOURCE_PATH = "python/0001-two-sum.py"
SOURCE_ID = "sample-two-sum"
FIXTURES = Path(__file__).resolve().parents[1] / "fixtures"
SOLUTION = FIXTURES / "two_sum_solutions" / "correct_hash_map.py"
# CRLF line endings and a missing final newline must both survive untouched.
SOURCE_BYTES = SOLUTION.read_bytes().replace(b"\r\n", b"\n").replace(b"\n", b"\r\n")
SOURCE_BYTES = SOURCE_BYTES.rstrip(b"\r\n")
LICENSE_BYTES = (
    b"MIT License\r\n\r\nCopyright (c) Example Authors\r\n\r\nPermission is\r\n"
)
ACQUIRED_AT = datetime(2026, 10, 28, 12, 0, tzinfo=UTC)


@pytest.fixture
def references(tmp_path: Path) -> Path:
    return tmp_path / "references"


def upstream_request(server: UpstreamServer, **overrides: Any) -> UpstreamRequest:
    fields: dict[str, Any] = {
        "source_id": SOURCE_ID,
        "repository": "https://github.com/example/sample",
        "revision": REVISION,
        "path": SOURCE_PATH,
        "license_path": "LICENSE",
        "license_identifier": "MIT",
        "license_terms": "Keep the copyright and permission notice with copies.",
        "policy_note": None,
        "language": "python",
        "classification": "reference_solution",
        "title": "Sample: Two Sum (Python)",
        "raw_base": server.base_url,
        "actor": "pytest",
    }
    fields.update(overrides)
    return UpstreamRequest(**fields)


def import_sample(references: Path, server: UpstreamServer) -> None:
    server.publish(REVISION, SOURCE_PATH, SOURCE_BYTES)
    server.publish(REVISION, "LICENSE", LICENSE_BYTES)
    add_upstream(
        references, upstream_request(server), fetcher=fetch_url, acquired_at=ACQUIRED_AT
    )


@pytest.fixture
def imported(references: Path, upstream_server: UpstreamServer) -> Path:
    import_sample(references, upstream_server)
    return references


def adapter_file(tmp_path: Path, body: bytes = b"# adapter\n") -> Path:
    path = tmp_path / "adapter_two_sum.py"
    path.write_bytes(body)
    return path


def adaptation_request(tmp_path: Path, **overrides: Any) -> LocalRequest:
    fields: dict[str, Any] = {
        "source_id": "sample-two-sum-adapter",
        "kind": "adaptation",
        "source_file": adapter_file(tmp_path),
        "language": "python",
        "classification": "reference_solution",
        "title": "Two Sum adapted for the local runner",
        "actor": "pytest",
        "derived_from": SOURCE_ID,
        "transformation": "Wrapped the class method in a plain function.",
    }
    fields.update(overrides)
    return LocalRequest(**fields)


def original_request(tmp_path: Path, **overrides: Any) -> LocalRequest:
    fields: dict[str, Any] = {
        "source_id": "sample-original",
        "kind": "original",
        "source_file": SOLUTION,
        "language": "python",
        "classification": "reference_solution",
        "title": "Agent-written Two Sum",
        "actor": "an agent",
        "derived_from": None,
        "transformation": None,
    }
    fields.update(overrides)
    return LocalRequest(**fields)


def tree(root: Path) -> list[str]:
    return sorted(
        p.relative_to(root).as_posix() for p in root.rglob("*") if p.is_file()
    )


def rewrite_manifest(
    references: Path, source_id: str, edit: Callable[[Any], None]
) -> None:
    path = references / "manifests" / f"{source_id}.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    edit(data)
    path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")


def test_add_preserves_served_bytes_exactly(imported: Path) -> None:
    upstream = imported / "upstream" / SOURCE_ID
    assert (upstream / "0001-two-sum.py").read_bytes() == SOURCE_BYTES
    assert (upstream / "LICENSE").read_bytes() == LICENSE_BYTES
    assert b"\r\n" in (upstream / "0001-two-sum.py").read_bytes()
    manifest = load_manifest(imported, SOURCE_ID)
    assert manifest.file.sha256 == sha256_hex(SOURCE_BYTES)
    assert manifest.license is not None
    assert manifest.license.notice.sha256 == sha256_hex(LICENSE_BYTES)
    assert tree(imported) == [
        f"manifests/{SOURCE_ID}.json",
        f"upstream/{SOURCE_ID}/0001-two-sum.py",
        f"upstream/{SOURCE_ID}/LICENSE",
    ]


def test_add_records_provenance_and_honest_evidence(
    imported: Path, upstream_server: UpstreamServer
) -> None:
    manifest = load_manifest(imported, SOURCE_ID)
    publication = manifest.evidence.publication
    assert publication.url == (
        f"https://github.com/example/sample/blob/{REVISION}/{SOURCE_PATH}"
    )
    assert publication.revision == REVISION
    assert publication.path == SOURCE_PATH
    assert manifest.acquisition.fetched_urls == (
        f"{upstream_server.base_url}/{REVISION}/{SOURCE_PATH}",
        f"{upstream_server.base_url}/{REVISION}/LICENSE",
    )
    assert manifest.acquisition.acquired_at == ACQUIRED_AT.isoformat()
    assert manifest.acquisition.method == "http_fetch"
    assert manifest.acquisition.actor == "pytest"
    assert manifest.acquisition.tool.name == "practice"
    assert manifest.acquisition.tool.version == version("leetcode-for-robots")
    assert manifest.evidence.platform_acceptance.status == "none"
    assert manifest.evidence.local_validation.status == "none"
    assert validation_state(manifest) == "none"
    assert verify_references(imported).problems == []


def test_manifest_file_is_lf_json_with_a_final_newline(imported: Path) -> None:
    raw = (imported / "manifests" / f"{SOURCE_ID}.json").read_bytes()
    assert b"\r" not in raw
    assert raw.endswith(b"}\n")


def test_injected_fetcher_sees_the_source_then_the_notice(
    references: Path, upstream_server: UpstreamServer
) -> None:
    upstream_server.publish(REVISION, SOURCE_PATH, SOURCE_BYTES)
    upstream_server.publish(REVISION, "LICENSE", LICENSE_BYTES)
    seen: list[str] = []

    def recording_fetcher(url: str) -> bytes:
        seen.append(url)
        return fetch_url(url)

    add_upstream(
        references, upstream_request(upstream_server), fetcher=recording_fetcher
    )
    assert [u.rsplit("/", 1)[-1] for u in seen] == ["0001-two-sum.py", "LICENSE"]


def test_adding_an_existing_id_is_refused_and_changes_nothing(
    imported: Path, upstream_server: UpstreamServer
) -> None:
    before = tree(imported)
    with pytest.raises(SourceError, match="already exists"):
        add_upstream(imported, upstream_request(upstream_server))
    assert tree(imported) == before


@pytest.mark.parametrize("missing", [SOURCE_PATH, "LICENSE"])
def test_a_failed_download_writes_nothing(
    references: Path, upstream_server: UpstreamServer, missing: str
) -> None:
    for path, data in ((SOURCE_PATH, SOURCE_BYTES), ("LICENSE", LICENSE_BYTES)):
        if path != missing:
            upstream_server.publish(REVISION, path, data)
    with pytest.raises(SourceError, match="404"):
        add_upstream(references, upstream_request(upstream_server))
    assert not references.exists() or tree(references) == []


def test_a_branch_name_is_not_an_exact_revision(
    references: Path, upstream_server: UpstreamServer
) -> None:
    with pytest.raises(SourceError, match="40"):
        add_upstream(references, upstream_request(upstream_server, revision="main"))
    assert not references.exists() or tree(references) == []


def test_notice_cannot_share_the_source_file_name(
    references: Path, upstream_server: UpstreamServer
) -> None:
    upstream_server.publish(REVISION, "LICENSE", LICENSE_BYTES)
    request = upstream_request(upstream_server, path="LICENSE")
    with pytest.raises(SourceError, match="same file name"):
        add_upstream(references, request)


def test_non_permissive_license_is_refused_without_a_policy_note(
    references: Path, upstream_server: UpstreamServer
) -> None:
    upstream_server.publish(REVISION, SOURCE_PATH, SOURCE_BYTES)
    upstream_server.publish(REVISION, "LICENSE", LICENSE_BYTES)
    request = upstream_request(upstream_server, license_identifier="CC-BY-SA-4.0")
    with pytest.raises(SourceError, match="policy_note"):
        add_upstream(references, request)
    assert not references.exists() or tree(references) == []
    noted = upstream_request(
        upstream_server,
        license_identifier="CC-BY-SA-4.0",
        policy_note="Noncommercial project; share-alike text stays in its own file.",
    )
    manifest = add_upstream(references, noted)
    assert manifest.license is not None
    assert manifest.license.policy_note is not None
    assert verify_references(references).problems == []


def test_redirects_are_refused(upstream_server: UpstreamServer) -> None:
    upstream_server.publish(REVISION, "elsewhere.py", b"x = 1\n")
    upstream_server.redirect(
        REVISION, "moved.py", f"{upstream_server.base_url}/{REVISION}/elsewhere.py"
    )
    with pytest.raises(FetchError, match="redirect"):
        fetch_url(f"{upstream_server.base_url}/{REVISION}/moved.py")


def test_oversized_responses_are_refused(upstream_server: UpstreamServer) -> None:
    url = upstream_server.publish(REVISION, "big.bin", b"x" * 100)
    assert fetch_url(url, max_bytes=100) == b"x" * 100
    with pytest.raises(FetchError, match="larger than"):
        fetch_url(url, max_bytes=99)


@pytest.mark.parametrize(
    "url", ["http://example.com/x", "file:///etc/passwd", "ftp://example.com/x"]
)
def test_only_https_or_loopback_http_is_fetched(url: str) -> None:
    with pytest.raises(FetchError, match="https"):
        fetch_url(url)


def test_unreachable_server_is_a_clear_error() -> None:
    with pytest.raises(FetchError, match="cannot fetch"):
        fetch_url("http://127.0.0.1:9/never")


def test_tampered_source_bytes_fail_verification(imported: Path) -> None:
    target = imported / "upstream" / SOURCE_ID / "0001-two-sum.py"
    target.write_bytes(SOURCE_BYTES.replace(b"\r\n", b"\n"))  # LF conversion
    problems = verify_references(imported).problems
    assert len(problems) == 1
    assert SOURCE_ID in problems[0]
    assert "upstream/sample-two-sum/0001-two-sum.py" in problems[0]
    assert "sha256 mismatch" in problems[0]
    assert sha256_hex(SOURCE_BYTES) in problems[0]


def test_tampered_notice_fails_verification(imported: Path) -> None:
    (imported / "upstream" / SOURCE_ID / "LICENSE").write_bytes(b"MIT License\n")
    problems = verify_references(imported).problems
    assert any("LICENSE" in p and "sha256 mismatch" in p for p in problems)


@pytest.mark.parametrize("name", ["0001-two-sum.py", "LICENSE"])
def test_missing_preserved_files_fail_verification(imported: Path, name: str) -> None:
    (imported / "upstream" / SOURCE_ID / name).unlink()
    problems = verify_references(imported).problems
    assert any(name in p and "missing" in p for p in problems)


@pytest.mark.parametrize("folder", ["upstream", "adaptations", "original"])
def test_unlisted_files_in_reference_folders_fail_verification(
    imported: Path, folder: str
) -> None:
    stray = imported / folder / "unlisted" / "helper.py"
    stray.parent.mkdir(parents=True, exist_ok=True)
    stray.write_bytes(b"print('hello')\n")
    problems = verify_references(imported).problems
    assert any(
        f"{folder}/unlisted/helper.py" in p and "not listed" in p for p in problems
    )


def test_a_missing_references_folder_is_reported(tmp_path: Path) -> None:
    report = verify_references(tmp_path / "nowhere")
    assert any("not found" in p for p in report.problems)


def test_an_unreadable_manifest_names_the_file(imported: Path) -> None:
    (imported / "manifests" / "broken.json").write_text("{not json", encoding="utf-8")
    problems = verify_references(imported).problems
    assert any("broken.json" in p and "JSON" in p for p in problems)


def test_manifest_file_name_must_match_its_id(imported: Path) -> None:
    source = imported / "manifests" / f"{SOURCE_ID}.json"
    source.rename(imported / "manifests" / "other-name.json")
    problems = verify_references(imported).problems
    assert any("other-name.json" in p and SOURCE_ID in p for p in problems)


def test_schema_errors_surface_through_verification(imported: Path) -> None:
    def add_field(data: Any) -> None:
        data["trust"] = "high"
        del data["language"]

    rewrite_manifest(imported, SOURCE_ID, add_field)
    problems = verify_references(imported).problems
    assert any("trust" in p and "unknown" in p for p in problems)
    assert any("language" in p and "missing" in p for p in problems)


def test_adaptation_is_stored_apart_and_inherits_only_the_notice(
    imported: Path, tmp_path: Path
) -> None:
    before = tree(imported)
    manifest = add_local(
        imported, adaptation_request(tmp_path), acquired_at=ACQUIRED_AT
    )
    upstream = load_manifest(imported, SOURCE_ID)
    assert manifest.kind == "adaptation"
    assert manifest.file.path == "adaptations/sample-two-sum-adapter/adapter_two_sum.py"
    assert manifest.derived_from == SOURCE_ID
    assert manifest.license == upstream.license
    assert manifest.evidence.publication.status == "unpublished"
    assert manifest.evidence.local_validation.status == "none"
    assert manifest.evidence.platform_acceptance.status == "none"
    assert [p for p in tree(imported) if p not in before] == [
        "adaptations/sample-two-sum-adapter/adapter_two_sum.py",
        "manifests/sample-two-sum-adapter.json",
    ]
    assert (
        imported / "upstream" / SOURCE_ID / "0001-two-sum.py"
    ).read_bytes() == SOURCE_BYTES
    assert verify_references(imported).problems == []


def test_adaptation_of_a_missing_upstream_is_refused_at_add_time(
    imported: Path, tmp_path: Path
) -> None:
    request = adaptation_request(tmp_path, derived_from="no-such-source")
    with pytest.raises(SourceError, match="no-such-source"):
        add_local(imported, request)


def test_adaptation_pointing_at_a_missing_upstream_fails_verification(
    imported: Path, tmp_path: Path
) -> None:
    add_local(imported, adaptation_request(tmp_path))
    rewrite_manifest(
        imported,
        "sample-two-sum-adapter",
        lambda data: data.update(derived_from="vanished"),
    )
    problems = verify_references(imported).problems
    assert any("derived_from" in p and "vanished" in p for p in problems)


def test_adaptation_must_derive_from_upstream_not_from_another_adaptation(
    imported: Path, tmp_path: Path
) -> None:
    add_local(imported, adaptation_request(tmp_path))
    second = adaptation_request(
        tmp_path, source_id="second", derived_from="sample-two-sum-adapter"
    )
    with pytest.raises(SourceError, match="upstream"):
        add_local(imported, second)


def test_adaptation_with_a_changed_license_fails_verification(
    imported: Path, tmp_path: Path
) -> None:
    add_local(imported, adaptation_request(tmp_path))

    def relabel(data: Any) -> None:
        data["license"]["identifier"] = "Apache-2.0"

    rewrite_manifest(imported, "sample-two-sum-adapter", relabel)
    problems = verify_references(imported).problems
    assert any("license" in p and "upstream" in p for p in problems)


def test_adapter_file_in_the_upstream_location_is_rejected(
    imported: Path, tmp_path: Path
) -> None:
    add_local(imported, adaptation_request(tmp_path))
    misplaced = imported / "upstream" / "sample-two-sum-adapter"
    misplaced.mkdir()
    (misplaced / "adapter_two_sum.py").write_bytes(b"# adapter\n")

    def move(data: Any) -> None:
        data["file"]["path"] = "upstream/sample-two-sum-adapter/adapter_two_sum.py"

    rewrite_manifest(imported, "sample-two-sum-adapter", move)
    problems = verify_references(imported).problems
    assert any("file.path" in p and "adaptations/" in p for p in problems)


def test_original_has_no_license_and_verifies(imported: Path, tmp_path: Path) -> None:
    manifest = add_local(imported, original_request(tmp_path), acquired_at=ACQUIRED_AT)
    assert manifest.license is None
    assert manifest.derived_from is None
    assert manifest.file.path == "original/sample-original/correct_hash_map.py"
    assert manifest.acquisition.method == "authored"
    assert verify_references(imported).problems == []


def test_add_local_rejects_unreadable_or_duplicate_requests(
    imported: Path, tmp_path: Path
) -> None:
    with pytest.raises(SourceError, match="cannot read"):
        add_local(
            imported, original_request(tmp_path, source_file=tmp_path / "nope.py")
        )
    add_local(imported, original_request(tmp_path))
    with pytest.raises(SourceError, match="already exists"):
        add_local(imported, original_request(tmp_path))
    with pytest.raises(SourceError, match="kind"):
        add_local(imported, original_request(tmp_path, source_id="x", kind="upstream"))


def run_fixture(solution: Path) -> Any:
    return run_exercise(load_package(FIXTURES / "two_sum"), solution)


def test_local_validation_is_bound_to_the_exact_code_that_ran(
    imported: Path,
) -> None:
    result = run_fixture(SOLUTION)
    assert result.status == "passed"
    # The preserved upstream bytes are CRLF Two Sum code; run those exact bytes.
    stored = imported / "upstream" / SOURCE_ID / "0001-two-sum.py"
    upstream_result = run_fixture(stored)
    manifest = record_validation(imported, SOURCE_ID, upstream_result)
    recorded = manifest.evidence.local_validation
    assert recorded.status == "passed"
    assert recorded.code_sha256 == sha256_hex(SOURCE_BYTES)
    assert recorded.suite_sha256 == upstream_result.suite_sha256
    assert recorded.runner == "practice run"
    assert validation_state(manifest) == "current"
    assert stored.read_bytes() == SOURCE_BYTES  # Recording never touches the code.
    assert verify_references(imported).problems == []


def test_validation_of_other_code_is_refused(imported: Path) -> None:
    other = run_fixture(FIXTURES / "two_sum_solutions" / "correct_brute_force.py")
    with pytest.raises(SourceError, match="different code"):
        record_validation(imported, SOURCE_ID, other)
    assert load_manifest(imported, SOURCE_ID).evidence.local_validation.status == "none"


def test_changed_code_makes_validation_stale_and_verification_fails(
    imported: Path,
) -> None:
    stored = imported / "upstream" / SOURCE_ID / "0001-two-sum.py"
    record_validation(imported, SOURCE_ID, run_fixture(stored))
    changed = SOURCE_BYTES + b"\r\n# edited\r\n"
    stored.write_bytes(changed)
    rewrite_manifest(
        imported,
        SOURCE_ID,
        lambda data: data["file"].update(sha256=sha256_hex(changed)),
    )
    manifest = load_manifest(imported, SOURCE_ID)
    assert validation_state(manifest) == "stale"
    problems = verify_references(imported).problems
    assert len(problems) == 1
    assert "stale" in problems[0]
    assert "not inherited" in problems[0]
    assert citation(imported, SOURCE_ID).local_validation == "stale"


def test_an_adaptation_never_inherits_the_upstream_validation(
    imported: Path, tmp_path: Path
) -> None:
    stored = imported / "upstream" / SOURCE_ID / "0001-two-sum.py"
    upstream = record_validation(imported, SOURCE_ID, run_fixture(stored))
    adapted = add_local(imported, adaptation_request(tmp_path))
    assert adapted.evidence.local_validation.status == "none"
    assert validation_state(adapted) == "none"

    copied = upstream.evidence.local_validation
    rewrite_manifest(
        imported,
        "sample-two-sum-adapter",
        lambda data: data["evidence"].update(
            local_validation={
                "status": copied.status,
                "code_sha256": copied.code_sha256,
                "run_at": copied.run_at,
                "suite_sha256": copied.suite_sha256,
                "suite_version": copied.suite_version,
                "runner": copied.runner,
            }
        ),
    )
    problems = verify_references(imported).problems
    assert any("sample-two-sum-adapter" in p and "stale" in p for p in problems)
    assert citation(imported, "sample-two-sum-adapter").local_validation == "stale"


def test_citation_for_upstream_carries_everything_an_export_needs(
    imported: Path,
) -> None:
    cited = citation(imported, SOURCE_ID)
    assert cited.id == SOURCE_ID
    assert cited.kind == "upstream"
    assert cited.title == "Sample: Two Sum (Python)"
    assert (
        cited.url == f"https://github.com/example/sample/blob/{REVISION}/{SOURCE_PATH}"
    )
    assert cited.repository == "https://github.com/example/sample"
    assert cited.revision == REVISION
    assert cited.path == SOURCE_PATH
    assert cited.license_identifier == "MIT"
    assert cited.license_terms is not None
    assert cited.license_terms.startswith("Keep the copyright")
    assert cited.notice_path == f"upstream/{SOURCE_ID}/LICENSE"
    assert cited.notice_sha256 == sha256_hex(LICENSE_BYTES)
    assert cited.file_sha256 == sha256_hex(SOURCE_BYTES)
    assert cited.classification == "reference_solution"
    assert cited.spoiler is is_spoiler("reference_solution")
    assert cited.language == "python"
    assert cited.derived_from is None
    assert cited.platform_acceptance == "none"
    assert cited.local_validation == "none"
    assert cited.to_dict()["revision"] == REVISION


def test_citation_for_adaptation_cites_the_upstream_source(
    imported: Path, tmp_path: Path
) -> None:
    add_local(imported, adaptation_request(tmp_path))
    cited = citation(imported, "sample-two-sum-adapter")
    assert cited.kind == "adaptation"
    assert cited.derived_from == SOURCE_ID
    assert cited.revision == REVISION
    assert cited.url == citation(imported, SOURCE_ID).url
    assert cited.license_identifier == "MIT"
    assert cited.file_sha256 != citation(imported, SOURCE_ID).file_sha256


def test_citation_for_original_has_no_upstream(imported: Path, tmp_path: Path) -> None:
    add_local(imported, original_request(tmp_path))
    cited = citation(imported, "sample-original")
    assert cited.kind == "original"
    assert cited.url is None
    assert cited.revision is None
    assert cited.license_identifier is None


def test_citation_refuses_tampered_material(imported: Path) -> None:
    (imported / "upstream" / SOURCE_ID / "0001-two-sum.py").write_bytes(b"x = 1\n")
    with pytest.raises(SourceError, match="sha256 mismatch"):
        citation(imported, SOURCE_ID)


def test_unknown_source_id_is_reported(imported: Path) -> None:
    with pytest.raises(SourceNotFoundError, match="nope"):
        citation(imported, "nope")
    with pytest.raises(SourceNotFoundError, match="nope"):
        load_manifest(imported, "nope")


def test_list_source_ids_is_sorted(imported: Path, tmp_path: Path) -> None:
    add_local(imported, original_request(tmp_path))
    assert list_source_ids(imported) == ["sample-original", SOURCE_ID]


def test_validate_source_runs_the_preserved_file_and_records_the_result(
    imported: Path,
) -> None:
    manifest = validate_source(imported, SOURCE_ID, FIXTURES / "two_sum")
    recorded = manifest.evidence.local_validation
    assert recorded.status == "passed"
    assert recorded.code_sha256 == sha256_hex(SOURCE_BYTES)
    assert recorded.suite_version == load_package(FIXTURES / "two_sum").suite.version  # type: ignore[union-attr]
    assert validation_state(manifest) == "current"
    assert verify_references(imported).problems == []


def test_validate_source_records_a_failing_run_honestly(
    imported: Path, tmp_path: Path
) -> None:
    wrong = FIXTURES / "two_sum_solutions" / "wrong_answer.py"
    add_local(
        imported, original_request(tmp_path, source_id="wrong", source_file=wrong)
    )
    manifest = validate_source(imported, "wrong", FIXTURES / "two_sum")
    assert manifest.evidence.local_validation.status == "failed"
    assert load_manifest(imported, "wrong").evidence.local_validation.status == "failed"


def test_validate_source_refuses_an_unknown_source(imported: Path) -> None:
    with pytest.raises(SourceNotFoundError):
        validate_source(imported, "nope", FIXTURES / "two_sum")


def test_validate_source_refuses_a_bad_package(imported: Path, tmp_path: Path) -> None:
    with pytest.raises(SourceError, match="not a directory"):
        validate_source(imported, SOURCE_ID, tmp_path / "missing")
    assert load_manifest(imported, SOURCE_ID).evidence.local_validation.status == "none"


@pytest.mark.parametrize("timeout", [0.0, -1.0, float("inf"), float("nan")])
def test_validate_source_refuses_a_nonsense_timeout(
    imported: Path, timeout: float
) -> None:
    with pytest.raises(SourceError, match="timeout"):
        validate_source(imported, SOURCE_ID, FIXTURES / "two_sum", timeout)
