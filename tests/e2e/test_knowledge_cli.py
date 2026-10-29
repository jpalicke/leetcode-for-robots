# ABOUTME: Runs the public knowledge command as a real installed CLI process.
# ABOUTME: Checks output creation, invalid inputs and absence of learner state.

import json
import os
import subprocess
import sys
from pathlib import Path

from practice.paths import REFERENCES_DIR


def test_export_process(problems_dir: Path, tmp_path: Path) -> None:
    private = tmp_path / "private"
    command = [
        str(
            Path(sys.executable).parent
            / ("practice.exe" if os.name == "nt" else "practice")
        ),
        "--problems-dir",
        str(problems_dir),
        "--references",
        str(REFERENCES_DIR),
        "--practice-dir",
        str(private),
        "knowledge",
        "export",
        "leetcode",
        "1",
    ]
    result = subprocess.run(command, capture_output=True, text=True, check=False)
    assert result.returncode == 0, result.stderr
    data = json.loads(result.stdout)
    assert [d["role"] for d in data["documents"]] == ["statement"]
    output = tmp_path / "export.json"
    result = subprocess.run(
        [*command, "--output", str(output)], capture_output=True, text=True, check=False
    )
    assert result.returncode == 0, result.stderr
    saved = output.read_bytes()
    assert json.loads(saved) == data
    result = subprocess.run(
        [*command, "--output", str(output)], capture_output=True, text=True, check=False
    )
    assert result.returncode == 3
    assert "Traceback" not in result.stderr
    assert output.read_bytes() == saved
    result = subprocess.run(
        [*command, "--hint-level", "99"], capture_output=True, text=True, check=False
    )
    assert result.returncode == 3
    assert "Traceback" not in result.stderr
    result = subprocess.run(
        [*command, "--output", str(problems_dir / "export.json")],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 3
    assert not (problems_dir / "export.json").exists()
    assert not private.exists()
