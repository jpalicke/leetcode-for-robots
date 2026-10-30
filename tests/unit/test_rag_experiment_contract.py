# ABOUTME: Validates the versioned pilot's identities, evidence and permission strata.
# ABOUTME: Keeps evaluator-only expectations separate from model-visible questions.

import json
from collections import Counter

from practice.paths import REPO_ROOT

DESIGN = REPO_ROOT / "experiments" / "rag"


def test_pilot_has_balanced_cases_and_explicit_permissions() -> None:
    protocol = json.loads((DESIGN / "protocol.json").read_text("utf-8"))
    cases = [
        json.loads(row) for row in (DESIGN / "cases.jsonl").read_text().splitlines()
    ]
    assert protocol["schema_version"] == 1
    assert protocol["status"] == "design_only"
    assert len(cases) == 42
    assert len({case["id"] for case in cases}) == len(cases)
    assert Counter(case["problem_id"] for case in cases) == dict.fromkeys(
        ["1", "20", "121", "217", "242", "704"], 7
    )
    assert Counter(case["stratum"] for case in cases) == dict.fromkeys(
        protocol["strata"], 6
    )
    for case in cases:
        assert case["platform"] == "leetcode"
        assert case["language"] == "python"
        assert case["question"] and case["gold"]["answer_requirements"]
        assert set(case["permissions"]) == {
            "mode",
            "hint_level",
            "reveal_solution",
            "source_ids",
        }
        assert case["expected_roles"]
        assert all(role in case["expected_roles"] for role in case["gold"]["roles"])
        assert case["conceptual_id"] == f"leetcode/{case['problem_id']}"
    assert protocol["private_indexing"] is False
    assert protocol["backend_selected"] is None


def test_protocol_names_the_reproducibility_artifacts() -> None:
    protocol = json.loads((DESIGN / "protocol.json").read_text("utf-8"))
    assert set(protocol["arms"]) == {"repository", "lexical", "dense"}
    assert protocol["top_k"] == [1, 3, 5]
    assert protocol["repeats"] == 3
    assert protocol["split"] == {
        "development": ["1", "217", "242"],
        "holdout": ["20", "121", "704"],
    }
    assert {
        "git_sha",
        "dataset_sha256",
        "exports",
        "model",
        "prompt_sha256",
        "tokenizer",
        "retriever",
        "ranked_chunks",
        "answers",
        "judgments",
    } <= set(protocol["required_run_artifacts"])
