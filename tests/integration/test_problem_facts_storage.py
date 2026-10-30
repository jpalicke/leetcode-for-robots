# ABOUTME: Checks facts publication against real filesystem and Git boundaries.
# ABOUTME: Existing files and staging artifacts remain intact on refusal or failure.

import subprocess
import sys
import tempfile
from pathlib import Path

import pytest

from practice.paths import REPO_ROOT
from tools.fetch_problem_facts import ToolError, output_directory, write_fact


def test_external_git_checkout_requires_actual_file_to_be_ignored(
    tmp_path: Path,
) -> None:
    subprocess.run(["git", "init", str(tmp_path)], capture_output=True, check=True)
    output = tmp_path / ".scratch" / "facts"
    with pytest.raises(ToolError, match="must be ignored"):
        output_directory(output, ["widget.json"])
    ignore = tmp_path / ".gitignore"
    ignore.write_text(".scratch/\n")
    assert output_directory(output, ["widget.json"]) == output.resolve()
    ignore.read_text()
    ignore.write_text(".scratch/*\n!.scratch/widget.json\n")
    with pytest.raises(ToolError, match="must be ignored"):
        output_directory(tmp_path / ".scratch", ["widget.json"])


def test_real_publication_never_clobbers_existing_files_or_stages(
    tmp_path: Path,
) -> None:
    unrelated = tmp_path / ".problem-facts-unrelated.tmp"
    unrelated.write_text("untouched")
    output = tmp_path / "widget.json"
    write_fact(output, {"example": "invented"})
    original = output.read_bytes()
    with pytest.raises(FileExistsError):
        write_fact(output, {"example": "other"})
    assert output.read_bytes() == original
    assert unrelated.read_text() == "untouched"
    assert {p.name for p in tmp_path.iterdir()} == {output.name, unrelated.name}


def test_corrupt_git_checkout_cannot_be_treated_as_external(tmp_path: Path) -> None:
    subprocess.run(["git", "init", str(tmp_path)], capture_output=True, check=True)
    config = tmp_path / ".git" / "config"
    config.read_text()
    config.write_text("[broken configuration")
    with pytest.raises(ToolError, match="Git"):
        output_directory(tmp_path / "facts", ["widget.json"])


def test_final_filename_ignore_does_not_leave_text_stages_unignored(
    tmp_path: Path,
) -> None:
    subprocess.run(["git", "init", str(tmp_path)], capture_output=True, check=True)
    (tmp_path / ".gitignore").write_text("widget.json\n")
    with pytest.raises(ToolError, match="stag"):
        output_directory(tmp_path, ["widget.json"])
    assert not list(tmp_path.glob(".problem-facts-*.tmp"))
    with pytest.raises(ToolError, match="stag"):
        write_fact(tmp_path / "widget.json", {"example": "invented source text"})
    assert not list(tmp_path.glob(".problem-facts-*.tmp"))
    assert not (tmp_path / "widget.json").exists()


def test_repository_source_output_is_refused() -> None:
    with pytest.raises(ToolError, match=".scratch"):
        output_directory(REPO_ROOT / "src" / "facts", ["widget.json"])


def test_scratch_link_cannot_escape_repository(tmp_path: Path) -> None:
    scratch = REPO_ROOT / ".scratch"
    scratch.mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory(dir=scratch) as temporary:
        link = Path(temporary) / "linked"
        if sys.platform == "win32":
            subprocess.run(
                ["cmd", "/c", "mklink", "/J", str(link), str(tmp_path)],
                capture_output=True,
                check=True,
            )
        else:
            link.symlink_to(tmp_path, target_is_directory=True)
        try:
            with pytest.raises(ToolError, match=".scratch"):
                output_directory(link / "facts", ["widget.json"])
            assert not (tmp_path / "facts").exists()
        finally:
            if sys.platform == "win32":
                link.rmdir()
            else:
                link.unlink()
