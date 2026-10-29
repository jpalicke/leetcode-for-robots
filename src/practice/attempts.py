# ABOUTME: Creates attempts and records tests, assistance, verdicts and finishes.
# ABOUTME: Each write is one journal event; attempt code files are never overwritten.

import hashlib
import os
import uuid
from dataclasses import dataclass
from datetime import date
from pathlib import Path

from practice import clock
from practice.catalog import Catalog
from practice.history import (
    Attempt,
    AttemptError,
    attempt_code_path,
    hash_file,
    journal_for,
)
from practice.journal import JournalError
from practice.package import ExercisePackage
from practice.rubric import ExplanationScores, RubricError
from practice.runner import RunResult, run_exercise

LANGUAGES = ("python",)
MODES = ("practice", "study")
ASSISTANCE_KINDS = ("hint", "reveal", "concept")
HINT_LEVELS = (0, 1, 2, 3)  # The ladder below a full reveal.
VERDICT_STATUSES = ("accepted", "rejected", "not_submitted")
STARTER_FILE = "starter.py"


@dataclass(frozen=True)
class StartedAttempt:
    attempt_id: str
    code_path: Path
    starter_source: str


def start_attempt(
    practice_dir: Path,
    catalog: Catalog,
    package: ExercisePackage,
    platform: str,
    problem_id: str,
    *,
    language: str,
    mode: str,
    timed: bool,
    review: bool = False,
) -> StartedAttempt:
    """Create a new blank attempt. Earlier attempts and their code are untouched."""
    if language not in LANGUAGES:
        raise AttemptError(f"unsupported language {language!r}; use one of {LANGUAGES}")
    if mode not in MODES:
        raise AttemptError(f"unknown mode {mode!r}; use one of {MODES}")
    if catalog.platform != platform:
        raise AttemptError(
            f"no catalog for platform {platform!r} (the catalog is {catalog.platform})"
        )
    entry = next(
        (e for e in catalog.entries if str(e.frontend_question_id) == problem_id), None
    )
    if entry is None:
        raise AttemptError(
            f"problem {problem_id!r} is not in the {platform} catalog; "
            f"try: practice search {problem_id}"
        )
    _require_package_matches(package, platform, problem_id)
    if package.language != language:
        raise AttemptError(f"the package is for {package.language}, not {language}")

    starter, starter_source = _starter_for(package)
    attempt_id = f"{clock.now():%Y%m%dT%H%M%SZ}-{uuid.uuid4().hex[:8]}"
    code_path = attempt_code_path(practice_dir, platform, problem_id, attempt_id)
    try:
        code_path.parent.mkdir(parents=True)
        with code_path.open("xb") as handle:  # Exclusive create: never overwrites.
            handle.write(starter)
            handle.flush()
            os.fsync(handle.fileno())
    except OSError as error:
        raise AttemptError(f"cannot create {code_path}: {error}") from error
    marker = {"review": True} if review else {}
    _append(
        practice_dir,
        "attempt_started",
        **marker,
        attempt_id=attempt_id,
        platform=platform,
        problem_id=problem_id,
        title=entry.title,
        language=language,
        mode=mode,
        timed=timed,
        code_path=code_path.relative_to(practice_dir).as_posix(),
        starter_source=starter_source,
        starter_sha256=hashlib.sha256(starter).hexdigest(),
    )
    return StartedAttempt(attempt_id, code_path, starter_source)


def run_attempt_tests(
    practice_dir: Path, attempt: Attempt, package: ExercisePackage, timeout: float
) -> RunResult:
    """Run the attempt's current code and journal the outcome as evidence."""
    _require_package_matches(package, attempt.platform, attempt.problem_id)
    code_path = attempt_code_path(
        practice_dir, attempt.platform, attempt.problem_id, attempt.attempt_id
    )
    try:
        result = run_exercise(package, code_path, timeout=timeout)
    except OSError as error:
        raise AttemptError(f"cannot read solution {code_path}: {error}") from error
    _append(
        practice_dir,
        "test_run",
        attempt_id=attempt.attempt_id,
        status=result.status,
        message=result.message,
        code_sha256=result.code_sha256,
        suite_sha256=result.suite_sha256,
        suite_version=result.suite_version,
        run_at=result.run_at,
        duration_seconds=result.duration_seconds,
        timeout_seconds=result.timeout_seconds,
        case_outcomes={case.case_id: case.outcome for case in result.cases},
    )
    return result


def record_assistance(
    practice_dir: Path,
    attempt: Attempt,
    kind: str,
    level: int | None,
    summary: str | None,
) -> None:
    """Record help that was actually delivered. Preparing a request is not help."""
    if kind not in ASSISTANCE_KINDS:
        raise AttemptError(f"unknown assistance kind {kind!r}; use {ASSISTANCE_KINDS}")
    if kind == "hint" and level not in HINT_LEVELS:
        raise AttemptError(
            f"a hint needs a level from {HINT_LEVELS[0]} to {HINT_LEVELS[-1]}"
        )
    if kind != "hint" and level is not None:
        raise AttemptError(f"only hints have a level; {kind} does not")
    fields: dict[str, object] = {"kind": kind, "level": level}
    if summary and summary.strip():
        fields["summary"] = summary.strip()
    _append(practice_dir, "assistance", attempt_id=attempt.attempt_id, **fields)


def record_verdict(
    practice_dir: Path,
    attempt: Attempt,
    status: str,
    source: str,
    verdict_date: str | None,
) -> None:
    """Record what the platform reported. This never changes the local result."""
    if status not in VERDICT_STATUSES:
        raise AttemptError(f"unknown verdict status {status!r}; use {VERDICT_STATUSES}")
    if not source.strip():
        raise AttemptError("a verdict needs a source, such as where you saw it")
    if verdict_date is None:
        verdict_date = clock.today().isoformat()
    try:
        date.fromisoformat(verdict_date)
    except ValueError as error:
        raise AttemptError(
            f"date must be an ISO date such as 2026-10-28, got {verdict_date!r}"
        ) from error
    code_path = attempt_code_path(
        practice_dir, attempt.platform, attempt.problem_id, attempt.attempt_id
    )
    _append(
        practice_dir,
        "platform_verdict",
        attempt_id=attempt.attempt_id,
        status=status,
        source=source.strip(),
        date=verdict_date,
        code_sha256=hash_file(code_path),
    )


def record_explanation(
    practice_dir: Path,
    attempt: Attempt,
    scores: ExplanationScores,
    evidence: str,
    feedback: str,
    coaching: str | None,
) -> None:
    """Record an explanation assessment of the code as it is now.

    It never changes completion, and earlier assessments are kept: a later one is
    a revision. Hints used and timing play no part in the scores.
    """
    try:
        scores.validate()
    except RubricError as error:
        raise AttemptError(str(error)) from error
    if not evidence.strip() or not feedback.strip():
        raise AttemptError("an assessment needs both evidence and feedback")
    code_path = attempt_code_path(
        practice_dir, attempt.platform, attempt.problem_id, attempt.attempt_id
    )
    fields: dict[str, object] = {
        **scores.to_fields(),
        "evidence": evidence.strip(),
        "feedback": feedback.strip(),
        "code_sha256": hash_file(code_path),
    }
    if coaching and coaching.strip():
        fields["coaching"] = coaching.strip()
    _append(
        practice_dir,
        "explanation_assessment",
        attempt_id=attempt.attempt_id,
        **fields,
    )


def finish_attempt(practice_dir: Path, attempt: Attempt) -> None:
    if attempt.finished_at is not None:
        raise AttemptError(f"attempt {attempt.attempt_id} is already finished")
    _append(practice_dir, "attempt_finished", attempt_id=attempt.attempt_id)


def _starter_for(package: ExercisePackage) -> tuple[bytes, str]:
    """The package's starter file, else a blank stub built from the signature."""
    starter_file = package.path / STARTER_FILE
    if starter_file.is_file():
        try:
            return starter_file.read_bytes(), "package starter"
        except OSError as error:
            raise AttemptError(f"cannot read {starter_file}: {error}") from error
    parameters = ", ".join(package.parameters)
    stub = f"def {package.function_name}({parameters}):\n    pass\n"
    return stub.encode("utf-8"), "generated stub"


def _require_package_matches(
    package: ExercisePackage, platform: str, problem_id: str
) -> None:
    if (package.platform, package.problem_id) != (platform, problem_id):
        raise AttemptError(
            f"the package describes {package.platform} {package.problem_id}, "
            f"not {platform} {problem_id}"
        )


def _append(practice_dir: Path, event_type: str, **fields: object) -> None:
    try:
        journal_for(practice_dir).append(event_type, **fields)
    except JournalError as error:
        raise AttemptError(str(error)) from error
