# ABOUTME: Integration tests for the real study units and the closed practice mode.
# ABOUTME: Uses the repository's own problems and references; nothing is mocked.

import json
from pathlib import Path

import pytest

from practice.knowledge import KnowledgeError, export_knowledge
from practice.paths import REFERENCES_DIR, REPO_ROOT
from practice.sources import load_manifest, verify_references
from practice.study import StudyError, handoff, study_units

PROBLEMS = REPO_ROOT / "problems"
STARTER_PROBLEMS = ("1", "20", "121", "217", "242", "704")
APPROVED_REPOSITORIES = (
    "https://github.com/krahets/hello-algo",
    "https://github.com/RunestoneInteractive/pythonds",
    "https://github.com/OpenDSA/OpenDSA",
)


def units_for(problem_id: str) -> tuple[str, ...]:
    return tuple(
        u.source_id
        for u in study_units(REFERENCES_DIR, PROBLEMS, "leetcode", problem_id)
    )


def test_every_starter_problem_lists_cited_study_units() -> None:
    for problem_id in STARTER_PROBLEMS:
        assert units_for(problem_id), problem_id


def test_units_cover_the_four_concepts() -> None:
    listed = {s for p in STARTER_PROBLEMS for s in units_for(p)}
    titles = " ".join(load_manifest(REFERENCES_DIR, s).title for s in listed).lower()

    for concept in ("hash", "stack", "binary search", "array"):
        assert concept in titles, concept


def test_each_unit_is_pinned_classified_and_carries_terms() -> None:
    listed = {s for p in STARTER_PROBLEMS for s in units_for(p)}

    for source_id in sorted(listed):
        manifest = load_manifest(REFERENCES_DIR, source_id)
        publication = manifest.evidence.publication
        assert manifest.kind == "upstream"
        assert manifest.classification in (
            "teaching_explanation",
            "algorithm_implementation",
            "reference_solution",
        )
        assert publication.repository in APPROVED_REPOSITORIES
        assert publication.revision is not None
        assert len(publication.revision) == 40
        assert manifest.license is not None
        assert manifest.license.notice is not None
        assert manifest.license.terms
        if manifest.license.identifier.startswith("CC-BY-NC-SA"):
            assert "NonCommercial" in manifest.license.terms
            assert "ShareAlike" in manifest.license.terms
            assert manifest.license.policy_note


def test_the_references_folder_still_verifies() -> None:
    report = verify_references(REFERENCES_DIR)

    assert report.problems == []


@pytest.mark.parametrize("problem_id", STARTER_PROBLEMS)
def test_practice_mode_never_exports_a_study_unit(
    problem_id: str, tmp_path: Path
) -> None:
    for source_id in units_for(problem_id):
        with pytest.raises(KnowledgeError, match="scope"):
            export_knowledge(
                PROBLEMS,
                REFERENCES_DIR,
                tmp_path / "private",
                "leetcode",
                problem_id,
                source_ids=(source_id,),
            )


@pytest.mark.parametrize("problem_id", STARTER_PROBLEMS)
def test_study_mode_exports_each_unit_with_its_citation(
    problem_id: str, tmp_path: Path
) -> None:
    for source_id in units_for(problem_id):
        body = export_knowledge(
            PROBLEMS,
            REFERENCES_DIR,
            tmp_path / "private",
            "leetcode",
            problem_id,
            mode="study",
            source_ids=(source_id,),
        )
        document = json.loads(body)["documents"][-1]
        assert document["citation"]["id"] == source_id
        assert document["citation"]["license_identifier"]
        assert document["notice"]


def test_a_problem_without_units_lists_none(tmp_path: Path) -> None:
    (tmp_path / "leetcode-9").mkdir()

    assert study_units(REFERENCES_DIR, tmp_path, "leetcode", "9") == ()


def test_a_unit_that_is_not_a_source_is_refused(tmp_path: Path) -> None:
    package = tmp_path / "leetcode-9"
    package.mkdir()
    (package / "readiness.json").write_text(
        json.dumps({"knowledge_sources": ["no-such-source"]}), encoding="utf-8"
    )

    with pytest.raises(StudyError):
        study_units(REFERENCES_DIR, tmp_path, "leetcode", "9")


def test_a_malformed_unit_list_is_refused(tmp_path: Path) -> None:
    package = tmp_path / "leetcode-9"
    package.mkdir()
    (package / "readiness.json").write_text(
        json.dumps({"knowledge_sources": "oops"}), encoding="utf-8"
    )

    with pytest.raises(StudyError, match="list of source IDs"):
        study_units(REFERENCES_DIR, tmp_path, "leetcode", "9")


def test_the_handoff_names_the_command_the_request_and_the_terms() -> None:
    units = study_units(REFERENCES_DIR, PROBLEMS, "leetcode", "704")

    text = handoff("leetcode", "704", units)

    for unit in units:
        assert (
            f"practice knowledge export leetcode 704 --mode study "
            f"--source {unit.source_id}"
        ) in text
        assert f"License {unit.license_identifier}:" in text
        assert unit.revision is not None and unit.revision in text
    assert "Paste-ready request for the tutor:" in text
    assert "never authorizes the full solution" in text
