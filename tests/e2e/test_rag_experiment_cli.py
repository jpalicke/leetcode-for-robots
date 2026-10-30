# ABOUTME: Verifies pilot scopes through the real installed knowledge command.
# ABOUTME: Confirms the documented CLI can produce deterministic evaluation inputs.

import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest

from practice.paths import REPO_ROOT

CASES = [
    json.loads(row)
    for row in (REPO_ROOT / "experiments/rag/cases.jsonl").read_text().splitlines()
    if json.loads(row)["problem_id"] == "1"
]


@pytest.mark.parametrize("case", CASES, ids=[case["id"] for case in CASES])
def test_pilot_cli_scopes(case: dict[str, Any], tmp_path: Path) -> None:
    record = case
    permissions = record["permissions"]
    private = tmp_path / "private"
    executable = Path(sys.executable).parent / (
        "practice.exe" if os.name == "nt" else "practice"
    )
    command = [
        str(executable),
        "--practice-dir",
        str(private),
        "knowledge",
        "export",
        record["platform"],
        record["problem_id"],
        "--mode",
        permissions["mode"],
    ]
    if permissions["hint_level"] is not None:
        command.extend(["--hint-level", str(permissions["hint_level"])])
    if permissions["reveal_solution"]:
        command.append("--reveal-solution")
    for source in permissions["source_ids"]:
        command.extend(["--source", source])
    runs = [
        subprocess.run(
            command,
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
        )
        for _ in range(2)
    ]
    for run in runs:
        assert run.returncode == 0, run.stderr
        assert run.stderr == ""
        assert sorted(
            doc["role"] for doc in json.loads(run.stdout)["documents"]
        ) == sorted(record["expected_roles"])
    assert runs[0].stdout == runs[1].stdout
    assert not private.exists()
