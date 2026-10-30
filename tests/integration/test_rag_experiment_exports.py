# ABOUTME: Checks every pilot scope against the actual public knowledge exporter.
# ABOUTME: Verifies source evidence is available without opening private learner files.

import json
from pathlib import Path
from typing import Any

import pytest

from practice.classification import LEARNER_CLASSES
from practice.knowledge import export_knowledge
from practice.paths import REPO_ROOT

CASES = [
    json.loads(row)
    for row in (REPO_ROOT / "experiments/rag/cases.jsonl").read_text().splitlines()
]


@pytest.mark.parametrize("case", CASES, ids=[case["id"] for case in CASES])
def test_case_permissions_have_real_export_evidence(
    case: dict[str, Any], tmp_path: Path
) -> None:
    # Each case uses an isolated private-directory sentinel.
    record = case
    permissions = record["permissions"]
    private = tmp_path / "learner"
    private.mkdir()
    sentinel = private / "journal.jsonl"
    sentinel.write_text("PRIVATE-RAG-CANARY: not valid JSON\n")
    before = sentinel.read_bytes()
    exported = export_knowledge(
        REPO_ROOT / "problems",
        REPO_ROOT / "references",
        private,
        record["platform"],
        record["problem_id"],
        language=record["language"],
        mode=permissions["mode"],
        hint_level=permissions["hint_level"],
        reveal_solution=permissions["reveal_solution"],
        source_ids=tuple(permissions["source_ids"]),
    )
    documents = json.loads(exported)["documents"]
    assert sorted(document["role"] for document in documents) == sorted(
        record["expected_roles"]
    )
    assert "PRIVATE-RAG-CANARY" not in exported
    assert sentinel.read_bytes() == before
    assert list(private.iterdir()) == [sentinel]
    assert all(
        document["content_kind"] not in LEARNER_CLASSES for document in documents
    )
    for document in documents:
        assert document["chunks"]
        if document["role"] == "source":
            assert (
                document["citation"]
                and document["source_id"] in permissions["source_ids"]
            )
        if document["role"].startswith("hint-"):
            assert document["role"] == f"hint-{permissions['hint_level']}"
        if document["role"] == "notes":
            assert permissions["reveal_solution"] is True
