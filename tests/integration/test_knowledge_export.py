# ABOUTME: Exercises deterministic exports using real problem and source files.
# ABOUTME: Checks privacy boundaries, source provenance and deterministic content.

import json
import shutil
from pathlib import Path
from typing import Any

import pytest

from practice.classification import LEARNER_CLASSES
from practice.knowledge import KnowledgeError, export_knowledge
from practice.paths import REPO_ROOT


@pytest.fixture
def inputs(tmp_path: Path) -> tuple[Path, Path, Path]:
    problems = tmp_path / "problems"
    shutil.copytree(REPO_ROOT / "problems" / "leetcode-1", problems / "leetcode-1")
    references = tmp_path / "references"
    shutil.copytree(REPO_ROOT / "references", references)
    return problems, references, tmp_path / "private"


def export(inputs: tuple[Path, Path, Path], **kwargs: Any) -> str:
    return export_knowledge(*inputs, "leetcode", "1", **kwargs)


def test_default_never_opens_excluded_bodies(inputs: tuple[Path, Path, Path]) -> None:
    problems, references, private = inputs
    package = problems / "leetcode-1"
    (package / "notes.md").unlink()
    shutil.rmtree(package / "hints")
    shutil.rmtree(references)
    (package / "tests.json").write_text("NOT JSON PRIVATE SENTINEL", encoding="utf-8")
    body = export(inputs)
    data = json.loads(body)
    assert [d["content_kind"] for d in data["documents"]] == ["statement_summary"]
    assert "SENTINEL" not in body
    assert not private.exists()
    assert export(inputs) == body


def test_hint_exact_and_solution_explicit(inputs: tuple[Path, Path, Path]) -> None:
    hint = json.loads(export(inputs, hint_level=2))
    assert [d["role"] for d in hint["documents"]] == ["statement", "hint-2"]
    reveal = json.loads(export(inputs, reveal_solution=True))
    assert [d["role"] for d in reveal["documents"]] == ["statement", "notes"]


def test_registered_reference_notice_and_tamper(
    inputs: tuple[Path, Path, Path],
) -> None:
    source = "neetcode-leetcode-0001-two-sum-python"
    with pytest.raises(KnowledgeError):
        export(inputs, source_ids=(source,))
    data = json.loads(export(inputs, source_ids=(source,), reveal_solution=True))
    doc = data["documents"][-1]
    assert doc["citation"]["license_identifier"] == "MIT"
    assert "Permission is hereby granted" in doc["notice"]
    assert len(doc["source_sha256"]) == 64
    path = inputs[1] / doc["citation"]["file_path"]
    path.write_text("tampered", encoding="utf-8")
    with pytest.raises(KnowledgeError, match="sha256 mismatch"):
        export(inputs, source_ids=(source,), reveal_solution=True)


@pytest.mark.parametrize("field,value", [("language", "java"), ("platform", "other")])
def test_identity_mismatch(
    inputs: tuple[Path, Path, Path], field: str, value: str
) -> None:
    path = inputs[0] / "leetcode-1" / "problem.json"
    data = json.loads(path.read_text("utf-8"))
    data[field] = value
    path.write_text(json.dumps(data), encoding="utf-8")
    with pytest.raises(KnowledgeError, match="match"):
        export(inputs)


@pytest.mark.parametrize(
    "name", ["../notes.md", ".practice/secret.md", "C:/private.md"]
)
def test_unsafe_selected_paths(inputs: tuple[Path, Path, Path], name: str) -> None:
    path = inputs[0] / "leetcode-1" / "readiness.json"
    record = json.loads(path.read_text("utf-8"))
    record["files"]["statement"]["path"] = name
    path.write_text(json.dumps(record), encoding="utf-8")
    with pytest.raises(KnowledgeError):
        export(inputs)


def test_copy_root_and_bounded_chunks(
    inputs: tuple[Path, Path, Path], tmp_path: Path
) -> None:
    statement = inputs[0] / "leetcode-1" / "statement.md"
    statement.write_text("paragraph\n" * 1500, encoding="utf-8")
    first = export(inputs)
    copied = tmp_path / "copy"
    shutil.copytree(inputs[0], copied / "problems")
    second = export_knowledge(
        copied / "problems", inputs[1], copied / "private", "leetcode", "1"
    )
    assert first == second
    chunks = json.loads(first)["documents"][0]["chunks"]
    assert len(chunks) > 1
    assert all(len(chunk["text"]) <= 2000 for chunk in chunks)
    assert "".join(chunk["text"] for chunk in chunks) == statement.read_bytes().decode(
        "utf-8"
    )
    statement.write_bytes(b"different body")
    changed = json.loads(export(inputs))["documents"][0]
    original = json.loads(first)["documents"][0]
    assert changed["id"] == original["id"]
    assert changed["chunks"][0]["id"] == original["chunks"][0]["id"]
    assert changed["content_sha256"] != original["content_sha256"]


def set_record(inputs: tuple[Path, Path, Path], record: dict[str, Any]) -> None:
    (inputs[0] / "leetcode-1" / "readiness.json").write_text(
        json.dumps(record), encoding="utf-8"
    )


def test_teaching_scope_and_language(inputs: tuple[Path, Path, Path]) -> None:
    from practice.sources import LocalRequest, add_local

    path = inputs[0] / "lesson.md"
    path.write_text("Concept prose may reveal a strategy.", encoding="utf-8")
    request = LocalRequest(
        source_id="lesson",
        kind="original",
        title="Lesson",
        language="python",
        classification="teaching_explanation",
        source_file=path,
        derived_from=None,
        transformation=None,
        actor="project",
    )
    add_local(inputs[1], request)
    record = json.loads(
        (inputs[0] / "leetcode-1" / "readiness.json").read_text("utf-8")
    )
    with pytest.raises(KnowledgeError, match="associated"):
        export(inputs, mode="study", source_ids=("lesson",))
    record["knowledge_sources"] = ["lesson"]
    set_record(inputs, record)
    with pytest.raises(KnowledgeError, match="scope"):
        export(inputs, source_ids=("lesson",))
    data = json.loads(export(inputs, mode="study", source_ids=("lesson",)))
    assert data["documents"][-1]["content_kind"] == "teaching_explanation"
    source = "neetcode-leetcode-0001-two-sum-python"
    with pytest.raises(KnowledgeError, match="scope"):
        export(inputs, mode="study", source_ids=(source,))
    manifest = inputs[1] / "manifests" / "lesson.json"
    content = json.loads(manifest.read_text("utf-8"))
    content["language"] = "java"
    manifest.write_text(json.dumps(content), encoding="utf-8")
    with pytest.raises(KnowledgeError, match="match"):
        export(inputs, mode="study", source_ids=("lesson",))


@pytest.mark.parametrize("kind", [*LEARNER_CLASSES, "test_data", "unknown"])
def test_reveal_cannot_admit_private_class(
    inputs: tuple[Path, Path, Path], kind: str
) -> None:
    record = json.loads(
        (inputs[0] / "leetcode-1" / "readiness.json").read_text("utf-8")
    )
    record["files"]["notes"]["content_class"] = kind
    set_record(inputs, record)
    with pytest.raises(KnowledgeError):
        export(inputs, reveal_solution=True)


def test_custom_private_root_rejected(inputs: tuple[Path, Path, Path]) -> None:
    with pytest.raises(KnowledgeError, match="private"):
        export_knowledge(inputs[0], inputs[1], inputs[0], "leetcode", "1")


def test_hint_index_relative_folder(inputs: tuple[Path, Path, Path]) -> None:
    package = inputs[0] / "leetcode-1"
    (package / "hints").rename(package / "nudges")
    record = json.loads((package / "readiness.json").read_text("utf-8"))
    record["files"]["hints"] = "nudges/index.json"
    set_record(inputs, record)
    assert "hint-2" in export(inputs, hint_level=2)


def test_adaptation_checks_upstream_and_notice(inputs: tuple[Path, Path, Path]) -> None:
    source = "neetcode-leetcode-0001-two-sum-python-function-adapter"
    data = json.loads(export(inputs, reveal_solution=True, source_ids=(source,)))
    doc = data["documents"][-1]
    assert doc["citation"]["derived_from"] == "neetcode-leetcode-0001-two-sum-python"
    assert doc["revision"] == doc["citation"]["revision"]
    assert doc["notice"]
    notice = inputs[1] / doc["citation"]["notice_path"]
    notice.write_bytes(b"tampered notice")
    with pytest.raises(KnowledgeError, match="sha256 mismatch"):
        export(inputs, reveal_solution=True, source_ids=(source,))


def test_selected_reference_private_path_rejected(
    inputs: tuple[Path, Path, Path],
) -> None:
    source = "neetcode-leetcode-0001-two-sum-python"
    path = inputs[1] / "manifests" / f"{source}.json"
    metadata = json.loads(path.read_text("utf-8"))
    metadata["file"]["path"] = f"upstream/{source}/.practice/code.py"
    path.write_text(json.dumps(metadata), encoding="utf-8")
    with pytest.raises(KnowledgeError, match="private"):
        export(inputs, reveal_solution=True, source_ids=(source,))


def test_copy_registered_sources_portable(
    inputs: tuple[Path, Path, Path], tmp_path: Path
) -> None:
    source = "neetcode-leetcode-0001-two-sum-python"
    first = export(inputs, reveal_solution=True, source_ids=(source,))
    copied = tmp_path / "copied"
    shutil.copytree(inputs[0], copied / "problems")
    shutil.copytree(inputs[1], copied / "references")
    second = export_knowledge(
        copied / "problems",
        copied / "references",
        copied / "private",
        "leetcode",
        "1",
        reveal_solution=True,
        source_ids=(source,),
    )
    assert first == second


def test_symlink_escape_and_excluded_private_sentinel(
    inputs: tuple[Path, Path, Path],
) -> None:
    package = inputs[0] / "leetcode-1"
    inputs[2].mkdir()
    sentinel = inputs[2] / "secret.md"
    sentinel.write_bytes(b"PRIVATE LEARNER SENTINEL")
    notes = package / "notes.md"
    notes.unlink()
    notes.symlink_to(sentinel)
    assert "PRIVATE LEARNER SENTINEL" not in export(inputs)
    with pytest.raises(KnowledgeError, match="private"):
        export(inputs, reveal_solution=True)
    statement = package / "statement.md"
    statement.unlink()
    outside = inputs[0] / "outside.md"
    outside.write_bytes(b"OUTSIDE SENTINEL")
    statement.symlink_to(outside)
    with pytest.raises(KnowledgeError, match="escapes"):
        export(inputs)


def test_adaptation_upstream_tamper(inputs: tuple[Path, Path, Path]) -> None:
    source = "neetcode-leetcode-0001-two-sum-python-function-adapter"
    upstream = (
        inputs[1]
        / "upstream"
        / "neetcode-leetcode-0001-two-sum-python"
        / "0001-two-sum.py"
    )
    upstream.write_bytes(b"tampered upstream")
    with pytest.raises(KnowledgeError, match="sha256 mismatch"):
        export(inputs, reveal_solution=True, source_ids=(source,))


@pytest.mark.parametrize("defect", ["kind", "identity"])
def test_adaptation_lineage_rejected_before_body_reads(
    inputs: tuple[Path, Path, Path], defect: str
) -> None:
    upstream_id = "neetcode-leetcode-0001-two-sum-python"
    adapter_id = f"{upstream_id}-function-adapter"
    path = inputs[1] / "manifests" / f"{upstream_id}.json"
    metadata = json.loads(path.read_text("utf-8"))
    if defect == "kind":
        adapter = inputs[1] / "manifests" / f"{adapter_id}.json"
        metadata = json.loads(adapter.read_text("utf-8"))
        metadata["id"] = upstream_id
        metadata["file"]["path"] = f"adaptations/{upstream_id}/absent.py"
        metadata["derived_from"] = "third-unselected-source"
    else:
        metadata["id"] = "different-upstream-id"
        metadata["file"]["path"] = "upstream/different-upstream-id/absent.py"
        metadata["license"]["notice"]["path"] = "upstream/different-upstream-id/LICENSE"
    path.write_text(json.dumps(metadata), encoding="utf-8")
    with pytest.raises(KnowledgeError, match="lineage must name the matching upstream"):
        export(inputs, reveal_solution=True, source_ids=(adapter_id,))
