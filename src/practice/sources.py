# ABOUTME: Intake, verification and citation of preserved reference sources.
# ABOUTME: Upstream bytes are stored and hashed, never executed, adapted or normalized.

import json
import math
import shutil
from collections.abc import Callable
from dataclasses import dataclass, replace
from datetime import UTC, datetime
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path, PurePosixPath
from typing import Any

from practice.classification import is_spoiler
from practice.package import PackageError, load_package
from practice.runner import RunResult, run_exercise
from practice.source_fetch import (
    Fetcher,
    FetchError,
    default_raw_base,
    fetch_url,
    raw_url,
)
from practice.source_manifest import (
    LOCATIONS,
    METHOD_FOR_KIND,
    SCHEMA_VERSION,
    SOURCE_ID_PATTERN,
    Acquisition,
    Evidence,
    FileRecord,
    LocalValidation,
    Manifest,
    ManifestError,
    PlatformAcceptance,
    Publication,
    Tool,
    sha256_hex,
    validation_state,
)

MANIFEST_DIR = "manifests"
TOOL_NAME = "practice"
DEFAULT_ACTOR = "practice sources add"
VALIDATION_RUNNER = "practice run"
PLACEHOLDER_SHA256 = "0" * 64  # Stands in while a request is checked before fetching.

# Hashes written once at import; nothing else in this module reads the schema's
# constants as data, so the value is only used to keep SCHEMA_VERSION referenced.
assert SCHEMA_VERSION == 1


class SourceError(Exception):
    """Intake, verification or lookup failed; `problems` lists each reason."""

    def __init__(self, message: str, problems: list[str] | None = None) -> None:
        super().__init__(message)
        self.problems = problems if problems is not None else [message]


class SourceNotFoundError(SourceError):
    """No manifest exists for the requested source id."""


@dataclass(frozen=True)
class UpstreamRequest:
    source_id: str
    repository: str  # For example https://github.com/OWNER/REPO.
    revision: str  # A full commit SHA, never a branch or tag.
    path: str  # The file's path inside the repository.
    license_path: str  # The notice's path inside the repository.
    license_identifier: str
    license_terms: str
    policy_note: str | None
    language: str
    classification: str
    title: str
    raw_base: str | None = None  # Defaults to GitHub's raw content host.
    actor: str = DEFAULT_ACTOR


@dataclass(frozen=True)
class LocalRequest:
    source_id: str
    kind: str  # "adaptation" or "original".
    source_file: Path
    language: str
    classification: str
    title: str
    actor: str
    derived_from: str | None
    transformation: str | None


@dataclass(frozen=True)
class VerifyReport:
    verified: list[str]
    problems: list[str]

    @property
    def ok(self) -> bool:
        return not self.problems


@dataclass(frozen=True)
class Citation:
    """Everything a downstream export needs to credit and trace one source."""

    id: str
    kind: str
    title: str
    language: str
    classification: str
    spoiler: bool
    url: str | None
    repository: str | None
    revision: str | None
    path: str | None
    license_identifier: str | None
    license_terms: str | None
    policy_note: str | None
    notice_path: str | None
    notice_sha256: str | None
    file_path: str
    file_sha256: str
    derived_from: str | None
    platform_acceptance: str
    local_validation: str  # none, current or stale.
    acquired_at: str

    def to_dict(self) -> dict[str, Any]:
        return dict(self.__dict__)


def tool_version() -> str:
    try:
        return version("leetcode-for-robots")
    except PackageNotFoundError:
        return "unknown"


def _now() -> datetime:
    return datetime.now(UTC)


def _timestamp(moment: datetime) -> str:
    return moment.isoformat(timespec="seconds")


def manifest_path(references: Path, source_id: str) -> Path:
    return references / MANIFEST_DIR / f"{source_id}.json"


def _manifest_bytes(manifest: Manifest) -> bytes:
    text = json.dumps(manifest.to_dict(), indent=2, ensure_ascii=False)
    return (text + "\n").encode("utf-8")  # LF everywhere, on every platform.


def _validated(manifest: Manifest) -> Manifest:
    """Run every schema rule over a manifest built in code."""
    try:
        return Manifest.from_dict(manifest.to_dict())
    except ManifestError as error:
        raise SourceError(
            f"{manifest.id or 'the entry'} is not valid: {'; '.join(error.problems)}",
            error.problems,
        ) from error


def _refuse_existing(references: Path, source_id: str) -> None:
    taken = [manifest_path(references, source_id)]
    taken += [references / folder / source_id for folder in LOCATIONS.values()]
    if any(path.exists() for path in taken):
        raise SourceError(f"source {source_id!r} already exists; nothing was changed")


def _write_all(
    references: Path, files: list[tuple[Path, bytes]], source_id: str
) -> None:
    try:
        for path, data in files:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(data)
    except OSError as error:
        for folder in LOCATIONS.values():
            shutil.rmtree(references / folder / source_id, ignore_errors=True)
        manifest_path(references, source_id).unlink(missing_ok=True)
        raise SourceError(f"cannot write {source_id}: {error}") from error


def _new_evidence(publication: Publication) -> Evidence:
    return Evidence(
        publication=publication,
        platform_acceptance=PlatformAcceptance("none", None, None),
        local_validation=LocalValidation("none", None, None, None, None, None),
    )


def add_upstream(
    references: Path,
    request: UpstreamRequest,
    fetcher: Fetcher = fetch_url,
    acquired_at: datetime | None = None,
) -> Manifest:
    """Fetch one upstream file and its notice, preserve both and write the manifest."""
    source_name = PurePosixPath(request.path).name
    notice_name = PurePosixPath(request.license_path).name
    if source_name == notice_name:
        raise SourceError(
            f"the source file and its notice have the same file name {source_name!r}"
        )
    try:
        base = request.raw_base or default_raw_base(request.repository)
    except FetchError as error:
        raise SourceError(str(error)) from error
    urls = (
        raw_url(base, request.revision, request.path),
        raw_url(base, request.revision, request.license_path),
    )

    def build(file_sha: str, notice_sha: str) -> Manifest:
        prefix = f"upstream/{request.source_id}"
        publication = Publication(
            status="published",
            url=(f"{request.repository}/blob/{request.revision}/{request.path}"),
            repository=request.repository,
            revision=request.revision,
            path=request.path,
        )
        from practice.source_manifest import LicenseRecord

        return Manifest(
            id=request.source_id,
            kind="upstream",
            title=request.title,
            language=request.language,
            classification=request.classification,
            file=FileRecord(f"{prefix}/{source_name}", file_sha),
            license=LicenseRecord(
                identifier=request.license_identifier,
                terms=request.license_terms,
                policy_note=request.policy_note,
                notice=FileRecord(f"{prefix}/{notice_name}", notice_sha),
            ),
            derived_from=None,
            transformation=None,
            acquisition=Acquisition(
                acquired_at=_timestamp(acquired_at or _now()),
                method=METHOD_FOR_KIND["upstream"],
                fetched_urls=urls,
                actor=request.actor,
                tool=Tool(TOOL_NAME, tool_version()),
            ),
            evidence=_new_evidence(publication),
        )

    _validated(build(PLACEHOLDER_SHA256, PLACEHOLDER_SHA256))  # Fail before fetching.
    _refuse_existing(references, request.source_id)
    try:
        source_bytes = fetcher(urls[0])
        notice_bytes = fetcher(urls[1])
    except FetchError as error:
        raise SourceError(str(error)) from error
    manifest = _validated(build(sha256_hex(source_bytes), sha256_hex(notice_bytes)))
    assert manifest.license is not None
    _write_all(
        references,
        [
            (references / manifest.file.path, source_bytes),
            (references / manifest.license.notice.path, notice_bytes),
            (manifest_path(references, manifest.id), _manifest_bytes(manifest)),
        ],
        manifest.id,
    )
    return manifest


def add_local(
    references: Path, request: LocalRequest, acquired_at: datetime | None = None
) -> Manifest:
    """Register an adaptation or original implementation, apart from upstream."""
    if request.kind not in ("adaptation", "original"):
        raise SourceError(
            f"kind must be adaptation or original, not {request.kind!r}; "
            "upstream files come from `sources add`"
        )
    license_record = None
    if request.kind == "adaptation":
        if not request.derived_from:
            raise SourceError("an adaptation needs derived_from, the upstream entry id")
        upstream = load_manifest(references, request.derived_from)
        if upstream.kind != "upstream":
            raise SourceError(
                f"{request.derived_from!r} is a {upstream.kind} entry; an "
                "adaptation must derive from an upstream entry"
            )
        license_record = upstream.license
    try:
        code = request.source_file.read_bytes()
    except OSError as error:
        raise SourceError(f"cannot read {request.source_file}: {error}") from error
    _refuse_existing(references, request.source_id)
    folder = LOCATIONS[request.kind]
    manifest = _validated(
        Manifest(
            id=request.source_id,
            kind=request.kind,
            title=request.title,
            language=request.language,
            classification=request.classification,
            file=FileRecord(
                f"{folder}/{request.source_id}/{request.source_file.name}",
                sha256_hex(code),
            ),
            license=license_record,
            derived_from=request.derived_from,
            transformation=request.transformation,
            acquisition=Acquisition(
                acquired_at=_timestamp(acquired_at or _now()),
                method=METHOD_FOR_KIND[request.kind],
                fetched_urls=(),
                actor=request.actor,
                tool=Tool(TOOL_NAME, tool_version()),
            ),
            evidence=_new_evidence(Publication("unpublished", None, None, None, None)),
        )
    )
    _write_all(
        references,
        [
            (references / manifest.file.path, code),
            (manifest_path(references, manifest.id), _manifest_bytes(manifest)),
        ],
        manifest.id,
    )
    return manifest


def list_source_ids(references: Path) -> list[str]:
    folder = references / MANIFEST_DIR
    if not folder.is_dir():
        return []
    return sorted(path.stem for path in folder.glob("*.json"))


def _read_manifest(path: Path) -> Manifest:
    try:
        text = path.read_text(encoding="utf-8")
        data = json.loads(text, parse_constant=_reject_constant)
    except (OSError, UnicodeDecodeError) as error:
        raise SourceError(f"cannot read: {error}") from error
    except ValueError as error:
        raise SourceError(f"is not valid JSON: {error}") from error
    try:
        return Manifest.from_dict(data)
    except ManifestError as error:
        raise SourceError("; ".join(error.problems), error.problems) from error


def _reject_constant(name: str) -> object:
    raise ValueError(f"{name} is not allowed in a manifest")


def load_manifest(references: Path, source_id: str) -> Manifest:
    path = manifest_path(references, source_id)
    if not SOURCE_ID_PATTERN.fullmatch(source_id) or not path.is_file():
        raise SourceNotFoundError(f"no source with id {source_id!r}")
    try:
        return _read_manifest(path)
    except SourceError as error:
        raise SourceError(
            f"{source_id}: {error}", [f"{source_id}: {p}" for p in error.problems]
        ) from error


def _check_preserved_file(
    references: Path, record: FileRecord, label: str
) -> list[str]:
    root = references.resolve()
    target = (references / record.path).resolve()
    if not target.is_relative_to(root):
        return [f"{label}: {record.path}: path leaves the references folder"]
    if not target.is_file():
        return [f"{label}: {record.path}: file is missing"]
    try:
        actual = sha256_hex(target.read_bytes())
    except OSError as error:
        return [f"{label}: {record.path}: cannot read: {error}"]
    if actual != record.sha256:
        return [
            f"{label}: {record.path}: sha256 mismatch "
            f"(manifest {record.sha256}, file {actual})"
        ]
    return []


def _check_entry(
    references: Path,
    manifest: Manifest,
    lookup: Callable[[str], Manifest | None],
) -> tuple[list[str], list[str]]:
    """Return (problems, stale notices) for one entry's bytes, notice and lineage."""
    label = manifest.id
    problems = _check_preserved_file(references, manifest.file, label)
    if manifest.license is not None:
        problems += _check_preserved_file(references, manifest.license.notice, label)
    if manifest.kind == "adaptation" and manifest.derived_from:
        upstream = lookup(manifest.derived_from)
        if upstream is None:
            problems.append(
                f"{label}: derived_from {manifest.derived_from!r}: no such source"
            )
        elif upstream.kind != "upstream":
            problems.append(
                f"{label}: derived_from {manifest.derived_from!r} is a "
                f"{upstream.kind} entry, not an upstream entry"
            )
        elif manifest.license != upstream.license:
            problems.append(
                f"{label}: license must match the upstream entry "
                f"{manifest.derived_from!r} (identifier, terms and notice)"
            )
    stale: list[str] = []
    if validation_state(manifest) == "stale":
        recorded = manifest.evidence.local_validation.code_sha256 or ""
        stale.append(
            f"{label}: local validation is stale: it covered code "
            f"{recorded[:12]} but the file is now {manifest.file.sha256[:12]}; "
            "evidence is not inherited, rerun the runner"
        )
    return problems, stale


def _raw_paths(data: object) -> set[str]:
    """Paths a manifest names, even when the rest of it fails the schema."""
    found: set[str] = set()
    if not isinstance(data, dict):
        return found
    candidates = [data.get("file")]
    license_data = data.get("license")
    if isinstance(license_data, dict):
        candidates.append(license_data.get("notice"))
    for candidate in candidates:
        if isinstance(candidate, dict) and isinstance(candidate.get("path"), str):
            found.add(candidate["path"])
    return found


def verify_references(references: Path) -> VerifyReport:
    """Check every manifest, every preserved byte hash and the folder contents."""
    if not references.is_dir():
        return VerifyReport([], [f"references folder not found: {references}"])
    problems: list[str] = []
    loaded: dict[str, Manifest] = {}
    listed: set[str] = set()
    for path in sorted((references / MANIFEST_DIR).glob("*.json")):
        try:
            manifest = _read_manifest(path)
        except SourceError as error:
            problems += [f"{path.name}: {p}" for p in error.problems]
            listed |= _raw_paths(_load_json_quietly(path))
            continue
        if manifest.id != path.stem:
            problems.append(
                f"{path.name}: manifest id {manifest.id!r} does not match the file name"
            )
        loaded[manifest.id] = manifest
        listed |= _raw_paths(manifest.to_dict())

    failing: set[str] = set()
    for manifest in loaded.values():
        found, stale = _check_entry(references, manifest, loaded.get)
        if found or stale:
            failing.add(manifest.id)
        problems += found + stale
    problems += _unlisted_files(references, listed)
    prefixes = tuple(f"{name}: " for name in failing)
    verified = [name for name in sorted(loaded) if name not in failing]
    del prefixes
    return VerifyReport(verified, problems)


def _load_json_quietly(path: Path) -> object:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


def _unlisted_files(references: Path, listed: set[str]) -> list[str]:
    problems = []
    for folder in LOCATIONS.values():
        for path in sorted((references / folder).rglob("*")):
            relative = path.relative_to(references).as_posix()
            if "__pycache__" in path.parts:
                continue  # Interpreter byte-code from running preserved code.
            if path.is_file() and relative not in listed:
                problems.append(
                    f"{relative}: file is not listed in any manifest; these folders "
                    "hold only manifest-listed material"
                )
    return problems


def citation(references: Path, source_id: str) -> Citation:
    """A citation record for a source; refuses material that fails verification."""
    manifest = load_manifest(references, source_id)

    def lookup(other: str) -> Manifest | None:
        try:
            return load_manifest(references, other)
        except SourceError:
            return None

    problems, _stale = _check_entry(references, manifest, lookup)
    if problems:
        raise SourceError(
            f"{source_id} fails verification: {'; '.join(problems)}", problems
        )
    origin = manifest
    if manifest.kind == "adaptation" and manifest.derived_from:
        upstream = lookup(manifest.derived_from)
        assert upstream is not None  # _check_entry reported it otherwise.
        origin = upstream
    publication = origin.evidence.publication
    license_record = manifest.license
    return Citation(
        id=manifest.id,
        kind=manifest.kind,
        title=manifest.title,
        language=manifest.language,
        classification=manifest.classification,
        spoiler=is_spoiler(manifest.classification),
        url=publication.url,
        repository=publication.repository,
        revision=publication.revision,
        path=publication.path,
        license_identifier=license_record.identifier if license_record else None,
        license_terms=license_record.terms if license_record else None,
        policy_note=license_record.policy_note if license_record else None,
        notice_path=license_record.notice.path if license_record else None,
        notice_sha256=license_record.notice.sha256 if license_record else None,
        file_path=manifest.file.path,
        file_sha256=manifest.file.sha256,
        derived_from=manifest.derived_from,
        platform_acceptance=manifest.evidence.platform_acceptance.status,
        local_validation=validation_state(manifest),
        acquired_at=manifest.acquisition.acquired_at,
    )


def record_validation(references: Path, source_id: str, result: RunResult) -> Manifest:
    """Bind a real runner result to the exact code it ran; nothing else is inherited."""
    manifest = load_manifest(references, source_id)
    if result.code_sha256 != manifest.file.sha256:
        raise SourceError(
            f"the run covered different code ({result.code_sha256[:12]}) than "
            f"{source_id} preserves ({manifest.file.sha256[:12]}); nothing was recorded"
        )
    problems = _check_preserved_file(references, manifest.file, source_id)
    if problems:
        raise SourceError("; ".join(problems), problems)
    evidence = replace(
        manifest.evidence,
        local_validation=LocalValidation(
            status=result.status,
            code_sha256=result.code_sha256,
            run_at=result.run_at,
            suite_sha256=result.suite_sha256,
            suite_version=result.suite_version,
            runner=VALIDATION_RUNNER,
        ),
    )
    updated = _validated(replace(manifest, evidence=evidence))
    manifest_path(references, source_id).write_bytes(_manifest_bytes(updated))
    return updated


def validate_source(
    references: Path, source_id: str, package: Path, timeout: float = 10.0
) -> Manifest:
    """Run the preserved file of one source against a package and record the result."""
    if not (math.isfinite(timeout) and timeout > 0):
        raise SourceError("the timeout must be a number of seconds above zero")
    manifest = load_manifest(references, source_id)
    try:
        exercise = load_package(package)
    except PackageError as error:
        raise SourceError(f"cannot validate {source_id}: {error}") from error
    try:
        result = run_exercise(exercise, references / manifest.file.path, timeout)
    except OSError as error:
        raise SourceError(f"cannot read {manifest.file.path}: {error}") from error
    return record_validation(references, source_id, result)
