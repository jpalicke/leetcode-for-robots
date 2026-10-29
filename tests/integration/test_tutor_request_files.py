# ABOUTME: Integration tests that prepare tutor requests against real attempts.
# ABOUTME: They prove the journal is untouched, requests stay private, failures loud.

from pathlib import Path

import pytest

from practice.attempts import finish_attempt, record_assistance, start_attempt
from practice.catalog import DEFAULT_CATALOG_PATH, load_catalog
from practice.history import AttemptError, find_attempt, load_history
from practice.package import load_package
from practice.paths import REPO_ROOT
from practice.tutor_request import (
    REQUESTS_DIR,
    PreparedRequest,
    RequestError,
    prepare_request,
)

PACKAGE_DIR = REPO_ROOT / "problems" / "leetcode-1"


@pytest.fixture
def practice_dir(tmp_path: Path) -> Path:
    return tmp_path / "learner"


@pytest.fixture
def attempt_id(practice_dir: Path) -> str:
    started = start_attempt(
        practice_dir,
        load_catalog(DEFAULT_CATALOG_PATH),
        load_package(PACKAGE_DIR),
        "leetcode",
        "1",
        language="python",
        mode="practice",
        timed=False,
    )
    return started.attempt_id


def prepare(
    practice_dir: Path, attempt_id: str, action: str, reveal: str | None = None
) -> PreparedRequest:
    return prepare_request(
        practice_dir,
        attempt_id,
        None,
        action=action,
        mode="practice",
        timed=False,
        reveal=reveal,
    )


def journal_bytes(practice_dir: Path) -> bytes:
    return (practice_dir / "journal.jsonl").read_bytes()


def test_preparing_a_hint_request_leaves_the_journal_byte_identical(
    practice_dir: Path, attempt_id: str
) -> None:
    before = journal_bytes(practice_dir)
    for action in ("hint", "stuck", "review-my-code", "concept-refresher"):
        prepare(practice_dir, attempt_id, action)
    prepare(practice_dir, attempt_id, "explain-solution", reveal="solution")
    assert journal_bytes(practice_dir) == before
    history = load_history(practice_dir)
    events = find_attempt(history, attempt_id).events
    assert [e["type"] for e in events] == ["attempt_started"]


def test_preparing_creates_no_lock_file_and_no_journal_when_none_exists(
    practice_dir: Path, attempt_id: str
) -> None:
    files_before = sorted(p.name for p in practice_dir.iterdir())
    prepare(practice_dir, attempt_id, "hint")
    files_after = sorted(p.name for p in practice_dir.iterdir())
    assert files_after == sorted([*files_before, REQUESTS_DIR])


def test_the_request_is_written_under_the_practice_directory(
    practice_dir: Path, attempt_id: str
) -> None:
    prepared = prepare(practice_dir, attempt_id, "hint")
    assert prepared.path.parent == practice_dir / REQUESTS_DIR
    assert prepared.path.name == f"{attempt_id}-1-hint.md"
    assert prepared.path.read_text(encoding="utf-8") == prepared.text


def test_requests_are_numbered_per_attempt_and_never_overwritten(
    practice_dir: Path, attempt_id: str
) -> None:
    first = prepare(practice_dir, attempt_id, "hint")
    second = prepare(practice_dir, attempt_id, "hint")
    third = prepare(practice_dir, attempt_id, "stuck")
    assert second.path.name == f"{attempt_id}-2-hint.md"
    assert third.path.name == f"{attempt_id}-3-stuck.md"
    assert first.path.exists() and second.path.exists()


def test_a_later_request_follows_recorded_assistance_not_preparation(
    practice_dir: Path, attempt_id: str
) -> None:
    again = prepare(practice_dir, attempt_id, "hint")
    assert "hint level 0 only" in again.text
    prepare(practice_dir, attempt_id, "hint")
    assert "hint level 0 only" in prepare(practice_dir, attempt_id, "hint").text
    attempt = find_attempt(load_history(practice_dir), attempt_id)
    record_assistance(practice_dir, attempt, "hint", 0, None)
    assert "hint level 1 only" in prepare(practice_dir, attempt_id, "hint").text


def test_default_request_location_is_inside_the_ignored_directory() -> None:
    # The default practice directory is .practice/ in the repository, which a
    # committed .gitignore rule covers; requests land beneath it.
    from practice.paths import resolve_practice_dir

    default = resolve_practice_dir(None, {})
    assert default == REPO_ROOT / ".practice"


def test_unknown_attempt_is_refused(practice_dir: Path, attempt_id: str) -> None:
    with pytest.raises(AttemptError, match="no attempt matches"):
        prepare(practice_dir, "nope", "hint")
    assert not (practice_dir / REQUESTS_DIR).exists()


def test_finished_attempt_is_refused_and_writes_nothing(
    practice_dir: Path, attempt_id: str
) -> None:
    finish_attempt(practice_dir, find_attempt(load_history(practice_dir), attempt_id))
    before = journal_bytes(practice_dir)
    with pytest.raises(RequestError, match="finished"):
        prepare(practice_dir, attempt_id, "hint")
    assert journal_bytes(practice_dir) == before
    assert not (practice_dir / REQUESTS_DIR).exists()


def test_unsupported_action_and_unclassified_reveal_write_nothing(
    practice_dir: Path, attempt_id: str
) -> None:
    with pytest.raises(RequestError, match="unsupported action"):
        prepare(practice_dir, attempt_id, "solve-it")
    with pytest.raises(RequestError, match="level 9"):
        prepare(practice_dir, attempt_id, "hint", reveal="9")
    with pytest.raises(RequestError, match="--reveal solution"):
        prepare(practice_dir, attempt_id, "explain-solution")
    assert not (practice_dir / REQUESTS_DIR).exists()


def test_pending_package_is_refused(
    practice_dir: Path, attempt_id: str, tmp_path: Path
) -> None:
    pending = tmp_path / "pending"
    pending.mkdir()
    (pending / "problem.json").write_text(
        '{"platform": "leetcode", "id": "1", "title": "Two Sum", '
        '"language": "python", "callable": {"adapter": "function", '
        '"name": "twoSum", "parameters": ["nums", "target"]}}',
        encoding="utf-8",
    )
    with pytest.raises(RequestError, match="not ready"):
        prepare_request(
            practice_dir,
            attempt_id,
            pending,
            action="hint",
            mode="practice",
            timed=False,
            reveal=None,
        )
    assert not (practice_dir / REQUESTS_DIR).exists()


def test_a_package_with_readiness_blockers_is_refused(
    practice_dir: Path, attempt_id: str, tmp_path: Path
) -> None:
    import json
    import shutil

    copy = tmp_path / "blocked"
    shutil.copytree(PACKAGE_DIR, copy)
    record = json.loads((copy / "readiness.json").read_text(encoding="utf-8"))
    record["blockers"] = ["hints are not reviewed"]
    (copy / "readiness.json").write_text(json.dumps(record), encoding="utf-8")
    with pytest.raises(RequestError, match="hints are not reviewed"):
        prepare_request(
            practice_dir,
            attempt_id,
            copy,
            action="hint",
            mode="practice",
            timed=False,
            reveal=None,
        )


def test_the_generated_file_holds_only_the_permitted_context(
    practice_dir: Path, attempt_id: str
) -> None:
    prepared = prepare(practice_dir, attempt_id, "hint", reveal="2")
    on_disk = prepared.path.read_text(encoding="utf-8")
    assert "hint level 2 only" in on_disk
    for level in (0, 1, 3):
        assert f"hints/{level}.md" not in on_disk
    notes_lines = {
        line.strip()
        for line in (PACKAGE_DIR / "notes.md").read_text(encoding="utf-8").splitlines()
        if len(line.strip()) >= 30
    }
    statement = (PACKAGE_DIR / "statement.md").read_text(encoding="utf-8")
    for line in notes_lines:
        if line not in statement:
            assert line not in on_disk
