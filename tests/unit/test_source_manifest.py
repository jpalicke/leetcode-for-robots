# ABOUTME: Unit tests for manifest validation, hashing and evidence staleness.
# ABOUTME: Manifests are plain dicts; every rejection must name the offending field.

import copy
import hashlib
from typing import Any

import pytest

from practice.source_manifest import (
    Manifest,
    ManifestError,
    sha256_hex,
    validation_state,
)

SHA_A = "a" * 64
SHA_B = "b" * 64
REVISION = "8fed5f7daa6a517e375a0562d876e4a72dfdafb8"


def upstream_dict() -> dict[str, Any]:
    return {
        "schema_version": 1,
        "id": "sample-two-sum",
        "kind": "upstream",
        "title": "Sample: Two Sum (Python)",
        "language": "python",
        "classification": "reference_solution",
        "file": {"path": "upstream/sample-two-sum/0001-two-sum.py", "sha256": SHA_A},
        "license": {
            "identifier": "MIT",
            "terms": "Keep the copyright and permission notice with copies.",
            "policy_note": None,
            "notice": {"path": "upstream/sample-two-sum/LICENSE", "sha256": SHA_B},
        },
        "derived_from": None,
        "transformation": None,
        "acquisition": {
            "acquired_at": "2026-10-28T12:00:00+00:00",
            "method": "http_fetch",
            "fetched_urls": [
                f"https://raw.githubusercontent.com/example/sample/{REVISION}/a.py",
                f"https://raw.githubusercontent.com/example/sample/{REVISION}/LICENSE",
            ],
            "actor": "practice sources add",
            "tool": {"name": "practice", "version": "0.1.0"},
        },
        "evidence": {
            "publication": {
                "status": "published",
                "url": f"https://github.com/example/sample/blob/{REVISION}/a.py",
                "repository": "https://github.com/example/sample",
                "revision": REVISION,
                "path": "a.py",
            },
            "platform_acceptance": {
                "status": "none",
                "platform": None,
                "evidence": None,
            },
            "local_validation": {
                "status": "none",
                "code_sha256": None,
                "run_at": None,
                "suite_sha256": None,
                "suite_version": None,
                "runner": None,
            },
        },
    }


def adaptation_dict() -> dict[str, Any]:
    data = upstream_dict()
    data.update(
        id="sample-two-sum-adapter",
        kind="adaptation",
        derived_from="sample-two-sum",
        transformation="Added the imports the judge supplies.",
    )
    data["file"] = {
        "path": "adaptations/sample-two-sum-adapter/two_sum.py",
        "sha256": SHA_A,
    }
    data["license"]["notice"] = {
        "path": "upstream/sample-two-sum/LICENSE",
        "sha256": SHA_B,
    }
    data["acquisition"] = {
        "acquired_at": "2026-10-28T12:00:00+00:00",
        "method": "local_adaptation",
        "fetched_urls": [],
        "actor": "an agent",
        "tool": {"name": "practice", "version": "0.1.0"},
    }
    data["evidence"]["publication"] = {
        "status": "unpublished",
        "url": None,
        "repository": None,
        "revision": None,
        "path": None,
    }
    return data


def original_dict() -> dict[str, Any]:
    data = adaptation_dict()
    data.update(
        id="sample-original",
        kind="original",
        license=None,
        derived_from=None,
        transformation=None,
    )
    data["file"] = {"path": "original/sample-original/two_sum.py", "sha256": SHA_A}
    data["acquisition"]["method"] = "authored"
    return data


def problems_for(data: dict[str, Any]) -> list[str]:
    with pytest.raises(ManifestError) as caught:
        Manifest.from_dict(data)
    return caught.value.problems


def test_sha256_hex_matches_hashlib() -> None:
    assert sha256_hex(b"abc") == hashlib.sha256(b"abc").hexdigest()


@pytest.mark.parametrize("build", [upstream_dict, adaptation_dict, original_dict])
def test_valid_manifests_round_trip_exactly(build: Any) -> None:
    data = build()
    assert Manifest.from_dict(data).to_dict() == data


def test_unknown_top_level_field_is_rejected() -> None:
    data = upstream_dict()
    data["trust_level"] = "high"
    assert any("trust_level" in p and "unknown" in p for p in problems_for(data))


def test_unknown_nested_field_is_rejected_with_its_path() -> None:
    data = upstream_dict()
    data["evidence"]["local_validation"]["inherited_from"] = "upstream"
    problems = problems_for(data)
    assert any(
        "evidence.local_validation" in p and "inherited_from" in p for p in problems
    )


@pytest.mark.parametrize(
    "path",
    [
        ("id",),
        ("kind",),
        ("title",),
        ("language",),
        ("classification",),
        ("file",),
        ("file", "sha256"),
        ("license",),
        ("license", "identifier"),
        ("license", "terms"),
        ("license", "policy_note"),
        ("license", "notice"),
        ("license", "notice", "sha256"),
        ("acquisition",),
        ("acquisition", "acquired_at"),
        ("acquisition", "fetched_urls"),
        ("acquisition", "actor"),
        ("acquisition", "tool", "version"),
        ("evidence", "publication", "revision"),
        ("evidence", "platform_acceptance"),
        ("evidence", "local_validation", "status"),
        ("schema_version",),
    ],
)
def test_every_required_field_is_reported_when_missing(path: tuple[str, ...]) -> None:
    data = upstream_dict()
    parent: Any = data
    for key in path[:-1]:
        parent = parent[key]
    del parent[path[-1]]
    problems = problems_for(data)
    assert any(path[-1] in p and "missing" in p for p in problems), problems


def test_several_problems_are_reported_together() -> None:
    data = upstream_dict()
    data["file"]["sha256"] = "xyz"
    data["language"] = ""
    data["classification"] = "bogus"
    assert len(problems_for(data)) >= 3


def test_non_object_input_is_rejected() -> None:
    with pytest.raises(ManifestError, match="object"):
        Manifest.from_dict(["not", "an", "object"])


def test_unsupported_schema_version_is_rejected() -> None:
    data = upstream_dict()
    data["schema_version"] = 2
    assert any("schema_version" in p for p in problems_for(data))


@pytest.mark.parametrize("value", ["abc", "A" * 64, "a" * 63, "g" * 64, 5])
def test_bad_sha256_is_rejected(value: Any) -> None:
    data = upstream_dict()
    data["file"]["sha256"] = value
    assert any("file.sha256" in p for p in problems_for(data))


@pytest.mark.parametrize("revision", ["main", "8fed5f7", "G" * 40, REVISION.upper()])
def test_revision_must_be_a_full_lowercase_commit_sha(revision: str) -> None:
    data = upstream_dict()
    data["evidence"]["publication"]["revision"] = revision
    assert any("revision" in p for p in problems_for(data))


@pytest.mark.parametrize(
    "path", ["/etc/passwd", "../x.py", "a/../../x.py", "a\\b.py", "C:/x.py", "a//b"]
)
def test_unsafe_paths_are_rejected(path: str) -> None:
    data = upstream_dict()
    data["file"]["path"] = path
    assert any("file.path" in p for p in problems_for(data))


@pytest.mark.parametrize("source_id", ["Bad_Id", "has space", "../escape", "", "-lead"])
def test_unsafe_ids_are_rejected(source_id: str) -> None:
    data = upstream_dict()
    data["id"] = source_id
    assert any("id" in p for p in problems_for(data))


def test_unknown_classification_is_rejected_with_choices() -> None:
    data = upstream_dict()
    data["classification"] = "solution"
    assert any("reference_solution" in p for p in problems_for(data))


@pytest.mark.parametrize(
    "identifier", ["CC-BY-SA-4.0", "CC-BY-NC-SA-4.0", "GPL-3.0-only"]
)
def test_non_permissive_license_requires_a_policy_note(identifier: str) -> None:
    data = upstream_dict()
    data["license"]["identifier"] = identifier
    assert any("policy_note" in p for p in problems_for(data))
    data["license"]["policy_note"] = "   "
    assert any("policy_note" in p for p in problems_for(data))
    data["license"]["policy_note"] = "Noncommercial project; share-alike kept apart."
    assert Manifest.from_dict(data).license is not None


@pytest.mark.parametrize("identifier", ["MIT", "Apache-2.0", "BSD-3-Clause", "CC0-1.0"])
def test_permissive_license_needs_no_policy_note(identifier: str) -> None:
    data = upstream_dict()
    data["license"]["identifier"] = identifier
    assert Manifest.from_dict(data).license is not None


def test_unknown_license_identifier_is_treated_as_non_permissive() -> None:
    data = upstream_dict()
    data["license"]["identifier"] = "Custom-Terms"
    assert any("policy_note" in p for p in problems_for(data))


def test_acquisition_time_must_carry_a_timezone() -> None:
    data = upstream_dict()
    data["acquisition"]["acquired_at"] = "2026-10-28T12:00:00"
    assert any("acquired_at" in p for p in problems_for(data))


def test_upstream_requires_published_evidence_and_matching_blob_url() -> None:
    data = upstream_dict()
    data["evidence"]["publication"]["url"] = "https://example.com/elsewhere"
    assert any("evidence.publication.url" in p for p in problems_for(data))
    data = upstream_dict()
    data["evidence"]["publication"] = adaptation_dict()["evidence"]["publication"]
    assert any("published" in p for p in problems_for(data))


def test_upstream_requires_fetch_evidence() -> None:
    data = upstream_dict()
    data["acquisition"]["fetched_urls"] = []
    assert any("fetched_urls" in p for p in problems_for(data))
    data = upstream_dict()
    data["acquisition"]["method"] = "authored"
    assert any("http_fetch" in p for p in problems_for(data))


def test_upstream_cannot_claim_a_derivation_or_transformation() -> None:
    data = upstream_dict()
    data["derived_from"] = "other"
    data["transformation"] = "edited"
    problems = problems_for(data)
    assert any("derived_from" in p for p in problems)
    assert any("transformation" in p for p in problems)


def test_upstream_files_must_live_in_the_upstream_location() -> None:
    data = upstream_dict()
    data["file"]["path"] = "adaptations/sample-two-sum/a.py"
    assert any("upstream/sample-two-sum/" in p for p in problems_for(data))
    data = upstream_dict()
    data["license"]["notice"]["path"] = "upstream/other/LICENSE"
    assert any("license.notice.path" in p for p in problems_for(data))


def test_adaptation_must_live_outside_the_upstream_location() -> None:
    data = adaptation_dict()
    data["file"]["path"] = "upstream/sample-two-sum/adapter.py"
    assert any("adaptations/sample-two-sum-adapter/" in p for p in problems_for(data))


def test_adaptation_needs_derived_from_and_a_transformation_record() -> None:
    data = adaptation_dict()
    data["derived_from"] = None
    data["transformation"] = None
    problems = problems_for(data)
    assert any("derived_from" in p for p in problems)
    assert any("transformation" in p for p in problems)


def test_adaptation_cannot_claim_upstream_acceptance_or_publication() -> None:
    data = adaptation_dict()
    data["evidence"]["platform_acceptance"] = {
        "status": "claimed_by_upstream",
        "platform": "leetcode",
        "evidence": "CONTRIBUTING.md",
    }
    assert any("claimed_by_upstream" in p for p in problems_for(data))
    data = adaptation_dict()
    data["evidence"]["publication"] = upstream_dict()["evidence"]["publication"]
    assert any("unpublished" in p for p in problems_for(data))


def test_adaptation_requires_the_upstream_license_and_notice() -> None:
    data = adaptation_dict()
    data["license"] = None
    assert any("license" in p for p in problems_for(data))
    data = adaptation_dict()
    data["license"]["notice"]["path"] = "adaptations/sample-two-sum-adapter/LICENSE"
    assert any("license.notice.path" in p for p in problems_for(data))


def test_original_has_no_upstream_links_or_license() -> None:
    data = original_dict()
    data["license"] = upstream_dict()["license"]
    data["derived_from"] = "sample-two-sum"
    problems = problems_for(data)
    assert any("license" in p for p in problems)
    assert any("derived_from" in p for p in problems)


def test_original_lives_in_the_original_location() -> None:
    data = original_dict()
    data["file"]["path"] = "adaptations/sample-original/two_sum.py"
    assert any("original/sample-original/" in p for p in problems_for(data))


def test_platform_acceptance_claims_need_a_platform_and_evidence() -> None:
    data = upstream_dict()
    data["evidence"]["platform_acceptance"] = {
        "status": "claimed_by_upstream",
        "platform": None,
        "evidence": None,
    }
    problems = problems_for(data)
    assert any("platform_acceptance.platform" in p for p in problems)
    assert any("platform_acceptance.evidence" in p for p in problems)
    data["evidence"]["platform_acceptance"] = {
        "status": "none",
        "platform": "leetcode",
        "evidence": None,
    }
    assert any("platform_acceptance.platform" in p for p in problems_for(data))


def test_unknown_platform_acceptance_status_is_rejected() -> None:
    data = upstream_dict()
    data["evidence"]["platform_acceptance"]["status"] = "probably_accepted"
    assert any("platform_acceptance.status" in p for p in problems_for(data))


def passed_validation(code_sha256: str) -> dict[str, Any]:
    return {
        "status": "passed",
        "code_sha256": code_sha256,
        "run_at": "2026-10-28T12:30:00+00:00",
        "suite_sha256": SHA_B,
        "suite_version": "1",
        "runner": "practice run",
    }


def test_local_validation_none_must_carry_no_run_details() -> None:
    data = upstream_dict()
    data["evidence"]["local_validation"]["code_sha256"] = SHA_A
    assert any("local_validation.code_sha256" in p for p in problems_for(data))


def test_local_validation_result_must_be_bound_to_a_code_hash() -> None:
    data = upstream_dict()
    data["evidence"]["local_validation"] = passed_validation(SHA_A)
    data["evidence"]["local_validation"]["code_sha256"] = None
    data["evidence"]["local_validation"]["run_at"] = None
    problems = problems_for(data)
    assert any("local_validation.code_sha256" in p for p in problems)
    assert any("local_validation.run_at" in p for p in problems)


def test_unknown_local_validation_status_is_rejected() -> None:
    data = upstream_dict()
    data["evidence"]["local_validation"] = passed_validation(SHA_A)
    data["evidence"]["local_validation"]["status"] = "great"
    assert any("local_validation.status" in p for p in problems_for(data))


def test_validation_state_none_current_and_stale() -> None:
    assert validation_state(Manifest.from_dict(upstream_dict())) == "none"
    current = upstream_dict()
    current["evidence"]["local_validation"] = passed_validation(SHA_A)
    assert validation_state(Manifest.from_dict(current)) == "current"
    stale = copy.deepcopy(current)
    stale["file"]["sha256"] = SHA_B  # The code changed after the run.
    assert validation_state(Manifest.from_dict(stale)) == "stale"
