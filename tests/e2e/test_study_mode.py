# ABOUTME: End-to-end tests for study mode through the real `practice` command line.
# ABOUTME: Study is an explicit opt-in; practice mode keeps study units closed.

import os
import re
import shlex
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

from practice.paths import REPO_ROOT


def command() -> Path:
    scripts = Path(sys.executable).parent
    return next(
        path
        for name in ("practice.exe", "practice")
        if (path := scripts / name).exists()
    )


@pytest.fixture
def learner(tmp_path: Path) -> Path:
    return tmp_path / "learner"


@pytest.fixture
def problems(tmp_path: Path) -> Path:
    root = tmp_path / "problems"
    shutil.copytree(REPO_ROOT / "problems" / "leetcode-1", root / "leetcode-1")
    return root


def practice(
    learner: Path, problems: Path | None, *args: str
) -> subprocess.CompletedProcess[str]:
    environment = os.environ.copy()
    environment["PRACTICE_DIR"] = str(learner)
    shared = ["--problems-dir", str(problems)] if problems else []
    return subprocess.run(
        [str(command()), *shared, *args],
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=120,
        check=False,
        env=environment,
    )


def test_study_is_a_real_main_menu_item(learner: Path, problems: Path) -> None:
    main = practice(learner, problems, "menu")

    assert main.returncode == 0, main.stderr
    assert "6. Study a concept" in main.stdout
    assert "Not available yet" not in main.stdout
    assert not (learner / "journal.jsonl").exists()

    screen = practice(learner, problems, "menu", "choose", "6")
    assert screen.returncode == 0, screen.stderr
    assert "practice menu choose N --study" in screen.stdout
    assert "1  Two Sum" in screen.stdout
    assert not (learner / "journal.jsonl").exists()


def test_choosing_a_problem_starts_study_mode_and_prints_the_handoff(
    learner: Path, problems: Path
) -> None:
    started = practice(learner, problems, "menu", "choose", "1", "--study")

    assert started.returncode == 0, started.stderr
    assert "(python, study, untimed)" in started.stdout
    assert "Paste-ready request for the tutor:" in started.stdout
    assert "License CC-BY-NC-SA-4.0:" in started.stdout
    assert "License MIT:" in started.stdout
    journal = (learner / "journal.jsonl").read_text(encoding="utf-8")
    assert '"mode":"study"' in journal.replace(" ", "")

    printed = re.findall(r"^  (practice knowledge export .+)$", started.stdout, re.M)
    assert len(printed) == 3
    for line in printed:
        argv = shlex.split(line)[1:]
        exported = practice(learner, None, *argv)
        assert exported.returncode == 0, exported.stderr
        assert '"citation"' in exported.stdout


def test_practice_mode_keeps_study_units_closed(learner: Path, problems: Path) -> None:
    started = practice(
        learner, problems, "menu", "choose", "1", "--problem", "leetcode", "1"
    )
    assert started.returncode == 0, started.stderr
    attempt_id = re.search(r"Started attempt (\S+)", started.stdout)
    assert attempt_id is not None

    refresher = practice(
        learner,
        problems,
        "request",
        attempt_id.group(1),
        "--action",
        "concept-refresher",
        "--package",
        str(problems / "leetcode-1"),
    )
    assert refresher.returncode == 0, refresher.stderr
    assert "ask the learner first" in refresher.stdout
    for marker in ("hello-algo", "opendsa", "runestone", "Hash Table"):
        assert marker not in refresher.stdout

    closed = practice(
        learner,
        None,
        "knowledge",
        "export",
        "leetcode",
        "1",
        "--source",
        "hello-algo-hash-table-concept",
    )
    assert closed.returncode == 3
    assert "excluded by the selected reveal scope" in closed.stderr
