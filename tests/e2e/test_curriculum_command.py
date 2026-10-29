# ABOUTME: Runs curriculum CLI through a real installed command and temporary files.
# ABOUTME: Checks safe output, failure codes and absence of private state writes.

import json
import subprocess
import sys
from pathlib import Path


def run_practice(*args: str) -> subprocess.CompletedProcess[str]:
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
        timeout=60,
        check=False,
    )


def test_curriculum_commands(tmp_path: Path) -> None:
    private = tmp_path / "private"
    for action in ("check", "next"):
        result = run_practice(
            "--practice-dir", str(private), "curriculum", action, "--json"
        )
        assert result.returncode == 0, result.stderr
        assert result.stderr == ""
        value = json.loads(result.stdout)
        if action == "next":
            assert value == [
                {
                    "label": "Objective 1",
                    "problems": [
                        {"platform": "leetcode", "problem_id": 1, "title": "Two Sum"}
                    ],
                }
            ]
    assert not private.exists()
    text = run_practice("curriculum", "next")
    assert text.stdout == "Objective 1\n  leetcode/1: Two Sum\n"
    bad = tmp_path / "bad.json"
    bad.write_text("{", encoding="utf-8")
    result = run_practice("curriculum", "check", "--file", str(bad))
    assert result.returncode == 3
    assert result.stdout == ""
    assert "Traceback" not in result.stderr
    assert run_practice("curriculum").returncode == 2


def test_custom_map_and_catalog_errors(tmp_path: Path) -> None:
    curriculum = tmp_path / "map.json"
    curriculum.write_text(
        json.dumps(
            {
                "version": 1,
                "platform": "leetcode",
                "concepts": [
                    {"id": "secret", "name": "Secret technique", "prerequisites": []}
                ],
                "starters": [704],
                "placements": [
                    {
                        "problem_id": 704,
                        "concept": "secret",
                        "prerequisites": [],
                        "label": "Secret technique",
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    result = run_practice("curriculum", "next", "--file", str(curriculum), "--json")
    assert result.returncode == 0, result.stderr
    assert result.stderr == ""
    assert json.loads(result.stdout) == [
        {
            "label": "Objective 1",
            "problems": [
                {"platform": "leetcode", "problem_id": 704, "title": "Binary Search"}
            ],
        }
    ]
    assert "secret" not in result.stdout.lower()
    missing = run_practice(
        "--catalog", str(tmp_path / "absent.json"), "curriculum", "check"
    )
    assert missing.returncode == 3
    assert missing.stdout == ""
    assert "cannot read catalog" in missing.stderr
