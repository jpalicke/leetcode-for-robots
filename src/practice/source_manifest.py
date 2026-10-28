# ABOUTME: Schema, strict validation and staleness rules for provenance manifests.
# ABOUTME: A manifest is plain JSON data; unknown fields and missing fields are errors.

import hashlib
import json
import re
from dataclasses import asdict, dataclass
from datetime import datetime
from typing import Any, Literal, get_args

from practice.classification import CONTENT_CLASSES
from practice.runner import Status as RunStatus

SCHEMA_VERSION = 1
KINDS = ("upstream", "adaptation", "original")
ACQUISITION_METHODS = ("http_fetch", "local_adaptation", "authored")
PUBLICATION_STATUSES = ("published", "unpublished")
# Platform acceptance is only ever recorded, never inferred from anything else.
PLATFORM_STATUSES = ("none", "claimed_by_upstream", "verified_by_us")
VALIDATION_STATUSES = ("none", *get_args(RunStatus))

# Where each kind of file may live under the references directory.
LOCATIONS = {
    "upstream": "upstream",
    "adaptation": "adaptations",
    "original": "original",
}
# Which acquisition method is the honest one for each kind.
METHOD_FOR_KIND = {
    "upstream": "http_fetch",
    "adaptation": "local_adaptation",
    "original": "authored",
}

# Every other license, including an unrecognized one, needs an explicit policy note.
PERMISSIVE_LICENSES = frozenset(
    {"MIT", "Apache-2.0", "BSD-2-Clause", "BSD-3-Clause", "ISC", "0BSD", "CC0-1.0"}
)

SHA256_PATTERN = re.compile(r"[0-9a-f]{64}")
COMMIT_SHA_PATTERN = re.compile(r"[0-9a-f]{40}")
SOURCE_ID_PATTERN = re.compile(r"[a-z0-9][a-z0-9-]{0,79}")
_LANGUAGE = re.compile(r"[a-z0-9][a-z0-9+#-]{0,31}")
_REPOSITORY = re.compile(r"https://[^\s/]+(/[^\s/]+)+")

ValidationState = Literal["none", "current", "stale"]


def sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


class ManifestError(Exception):
    """A manifest breaks the schema; `problems` lists every specific reason."""

    def __init__(self, problems: list[str]) -> None:
        super().__init__("; ".join(problems))
        self.problems = problems


@dataclass(frozen=True)
class FileRecord:
    path: str  # Relative to the references directory, with forward slashes.
    sha256: str


@dataclass(frozen=True)
class LicenseRecord:
    identifier: str
    terms: str
    policy_note: str | None
    notice: FileRecord


@dataclass(frozen=True)
class Tool:
    name: str
    version: str


@dataclass(frozen=True)
class Acquisition:
    acquired_at: str
    method: str
    fetched_urls: tuple[str, ...]
    actor: str
    tool: Tool


@dataclass(frozen=True)
class Publication:
    status: str
    url: str | None
    repository: str | None
    revision: str | None
    path: str | None


@dataclass(frozen=True)
class PlatformAcceptance:
    status: str
    platform: str | None
    evidence: str | None


@dataclass(frozen=True)
class LocalValidation:
    status: str
    code_sha256: str | None  # The exact code the run covered.
    run_at: str | None
    suite_sha256: str | None
    suite_version: str | None
    runner: str | None


@dataclass(frozen=True)
class Evidence:
    publication: Publication
    platform_acceptance: PlatformAcceptance
    local_validation: LocalValidation


@dataclass(frozen=True)
class Manifest:
    id: str
    kind: str
    title: str
    language: str
    classification: str
    file: FileRecord
    license: LicenseRecord | None
    derived_from: str | None
    transformation: str | None
    acquisition: Acquisition
    evidence: Evidence

    def to_dict(self) -> dict[str, Any]:
        body = {"schema_version": SCHEMA_VERSION, **asdict(self)}
        return json.loads(json.dumps(body))  # type: ignore[no-any-return]

    @classmethod
    def from_dict(cls, data: object) -> "Manifest":
        problems: list[str] = []
        manifest = _parse(data, problems)
        if problems:
            raise ManifestError(problems)
        return manifest


def validation_state(manifest: Manifest) -> ValidationState:
    """Local validation counts only for the exact code it ran against."""
    recorded = manifest.evidence.local_validation
    if recorded.status == "none":
        return "none"
    return "current" if recorded.code_sha256 == manifest.file.sha256 else "stale"


class _Reader:
    """Reads one JSON object, recording a specific problem for every defect."""

    def __init__(self, data: object, where: str, problems: list[str]) -> None:
        self._where = where
        self._problems = problems
        self._seen: set[str] = set()
        self._dead = False
        self._data: dict[str, Any] = {}
        if isinstance(data, dict):
            self._data = data
        else:
            problems.append(f"{where or 'the manifest'} must be an object")
            self._dead = True

    @classmethod
    def absent(cls, where: str, problems: list[str]) -> "_Reader":
        reader = cls({}, where, problems)
        reader._dead = True  # The parent already reported it; stay quiet.
        return reader

    def label(self, key: str) -> str:
        return f"{self._where}.{key}" if self._where else key

    def problem(self, key: str, message: str) -> None:
        self._problems.append(f"{self.label(key)} {message}")

    def _get(self, key: str) -> tuple[bool, Any]:
        self._seen.add(key)
        if key in self._data:
            return True, self._data[key]
        if not self._dead:
            self.problem(key, "is missing")
        return False, None

    def text(
        self,
        key: str,
        *,
        pattern: re.Pattern[str] | None = None,
        describe: str = "",
        choices: tuple[str, ...] | None = None,
    ) -> str:
        found, value = self._get(key)
        return self._checked_text(key, found, value, pattern, describe, choices) or ""

    def nullable_text(
        self,
        key: str,
        *,
        pattern: re.Pattern[str] | None = None,
        describe: str = "",
        choices: tuple[str, ...] | None = None,
    ) -> str | None:
        found, value = self._get(key)
        if not found or value is None:
            return None
        return self._checked_text(key, found, value, pattern, describe, choices)

    def _checked_text(
        self,
        key: str,
        found: bool,
        value: Any,
        pattern: re.Pattern[str] | None,
        describe: str,
        choices: tuple[str, ...] | None,
    ) -> str | None:
        if not found:
            return None
        if not isinstance(value, str) or not value.strip():
            self.problem(key, "must be a non-empty string")
            return None
        if pattern is not None and not pattern.fullmatch(value):
            self.problem(key, f"must be {describe}")
            return None
        if choices is not None and value not in choices:
            self.problem(key, f"must be one of: {', '.join(choices)}")
            return None
        return value

    def timestamp(self, key: str, *, nullable: bool = False) -> str | None:
        value = self.nullable_text(key) if nullable else self.text(key)
        if not value:
            return None
        try:
            parsed = datetime.fromisoformat(value)
        except ValueError:
            self.problem(key, "must be an ISO 8601 timestamp")
            return None
        if parsed.tzinfo is None:
            self.problem(key, "must include a timezone offset")
            return None
        return value

    def relative_path(self, key: str, *, nullable: bool = False) -> str | None:
        value = self.nullable_text(key) if nullable else self.text(key)
        if value and not _is_safe_relative(value):
            self.problem(key, "must be a relative path with forward slashes")
            return None
        return value or None

    def sha256(self, key: str, *, nullable: bool = False) -> str | None:
        kwargs: dict[str, Any] = {
            "pattern": SHA256_PATTERN,
            "describe": "64 lowercase hex digits",
        }
        value = (
            self.nullable_text(key, **kwargs) if nullable else self.text(key, **kwargs)
        )
        return value or None

    def integer(self, key: str) -> int | None:
        found, value = self._get(key)
        if not found:
            return None
        if isinstance(value, bool) or not isinstance(value, int):
            self.problem(key, "must be an integer")
            return None
        return value

    def text_list(self, key: str) -> tuple[str, ...]:
        found, value = self._get(key)
        if not found:
            return ()
        if not isinstance(value, list) or not all(
            isinstance(item, str) and item.strip() for item in value
        ):
            self.problem(key, "must be a list of non-empty strings")
            return ()
        return tuple(value)

    def child(self, key: str) -> "_Reader":
        found, value = self._get(key)
        if not found:
            return _Reader.absent(self.label(key), self._problems)
        return _Reader(value, self.label(key), self._problems)

    def nullable_child(self, key: str) -> "_Reader | None":
        found, value = self._get(key)
        if not found or value is None:
            return None
        return _Reader(value, self.label(key), self._problems)

    def finish(self) -> None:
        for key in self._data:
            if key not in self._seen:
                self.problem(key, "is an unknown field")


def _is_safe_relative(path: str) -> bool:
    if "\\" in path or path.startswith("/") or ":" in path:
        return False
    return all(part not in ("", ".", "..") for part in path.split("/"))


def _parse(data: object, problems: list[str]) -> Manifest:
    reader = _Reader(data, "", problems)
    version = reader.integer("schema_version")
    if version is not None and version != SCHEMA_VERSION:
        reader.problem("schema_version", f"must be {SCHEMA_VERSION}, not {version}")
    source_id = reader.text(
        "id", pattern=SOURCE_ID_PATTERN, describe="lowercase letters, digits, -"
    )
    kind = reader.text("kind", choices=KINDS)
    title = reader.text("title")
    language = reader.text(
        "language", pattern=_LANGUAGE, describe="a short lowercase language name"
    )
    classification = reader.text("classification", choices=tuple(CONTENT_CLASSES))
    file = _parse_file(reader.child("file"))
    license_reader = reader.nullable_child("license")
    license_record = _parse_license(license_reader) if license_reader else None
    derived_from = reader.nullable_text(
        "derived_from",
        pattern=SOURCE_ID_PATTERN,
        describe="the id of an upstream entry",
    )
    transformation = reader.nullable_text("transformation")
    acquisition = _parse_acquisition(reader.child("acquisition"))
    evidence = _parse_evidence(reader.child("evidence"))
    reader.finish()

    manifest = Manifest(
        id=source_id,
        kind=kind,
        title=title,
        language=language,
        classification=classification,
        file=file,
        license=license_record,
        derived_from=derived_from,
        transformation=transformation,
        acquisition=acquisition,
        evidence=evidence,
    )
    _check_rules(manifest, license_reader is not None, problems)
    return manifest


def _parse_file(reader: _Reader) -> FileRecord:
    record = FileRecord(
        path=reader.relative_path("path") or "", sha256=reader.sha256("sha256") or ""
    )
    reader.finish()
    return record


def _parse_license(reader: _Reader) -> LicenseRecord:
    record = LicenseRecord(
        identifier=reader.text("identifier"),
        terms=reader.text("terms"),
        policy_note=reader.nullable_text("policy_note"),
        notice=_parse_file(reader.child("notice")),
    )
    reader.finish()
    return record


def _parse_acquisition(reader: _Reader) -> Acquisition:
    tool_reader = reader.child("tool")
    tool = Tool(name=tool_reader.text("name"), version=tool_reader.text("version"))
    tool_reader.finish()
    record = Acquisition(
        acquired_at=reader.timestamp("acquired_at") or "",
        method=reader.text("method", choices=ACQUISITION_METHODS),
        fetched_urls=reader.text_list("fetched_urls"),
        actor=reader.text("actor"),
        tool=tool,
    )
    reader.finish()
    return record


def _parse_evidence(reader: _Reader) -> Evidence:
    publication_reader = reader.child("publication")
    publication = Publication(
        status=publication_reader.text("status", choices=PUBLICATION_STATUSES),
        url=publication_reader.nullable_text("url"),
        repository=publication_reader.nullable_text(
            "repository", pattern=_REPOSITORY, describe="an https repository URL"
        ),
        revision=publication_reader.nullable_text(
            "revision",
            pattern=COMMIT_SHA_PATTERN,
            describe="a full 40 character lowercase commit SHA",
        ),
        path=publication_reader.relative_path("path", nullable=True),
    )
    publication_reader.finish()

    acceptance_reader = reader.child("platform_acceptance")
    acceptance = PlatformAcceptance(
        status=acceptance_reader.text("status", choices=PLATFORM_STATUSES),
        platform=acceptance_reader.nullable_text("platform"),
        evidence=acceptance_reader.nullable_text("evidence"),
    )
    acceptance_reader.finish()

    validation_reader = reader.child("local_validation")
    validation = LocalValidation(
        status=validation_reader.text("status", choices=VALIDATION_STATUSES),
        code_sha256=validation_reader.sha256("code_sha256", nullable=True),
        run_at=validation_reader.timestamp("run_at", nullable=True),
        suite_sha256=validation_reader.sha256("suite_sha256", nullable=True),
        suite_version=validation_reader.nullable_text("suite_version"),
        runner=validation_reader.nullable_text("runner"),
    )
    validation_reader.finish()
    reader.finish()
    return Evidence(publication, acceptance, validation)


def _check_rules(manifest: Manifest, has_license: bool, problems: list[str]) -> None:
    kind = manifest.kind
    if kind not in KINDS:
        return  # Already reported; the remaining rules depend on the kind.
    evidence = manifest.evidence
    prefix = f"{LOCATIONS[kind]}/{manifest.id}/"

    def fail(label: str, message: str) -> None:
        problems.append(f"{label} {message}")

    if manifest.file.path and not manifest.file.path.startswith(prefix):
        fail("file.path", f"must be under {prefix} for {kind} material")

    _check_license(manifest, has_license, prefix, fail)

    wants_link = kind == "adaptation"
    if wants_link and not manifest.derived_from:
        fail("derived_from", "is required: name the upstream entry it adapts")
    if not wants_link and manifest.derived_from is not None:
        fail("derived_from", f"must be null for {kind} material")
    if wants_link and not manifest.transformation:
        fail("transformation", "is required: record what the adaptation changed")
    if not wants_link and manifest.transformation is not None:
        fail("transformation", f"must be null for {kind} material")

    acquisition = manifest.acquisition
    expected_method = METHOD_FOR_KIND[kind]
    if (
        acquisition.method in ACQUISITION_METHODS
        and acquisition.method != expected_method
    ):
        fail("acquisition.method", f"must be {expected_method} for {kind} material")
    if kind == "upstream" and not acquisition.fetched_urls:
        fail("acquisition.fetched_urls", "must list the URLs actually fetched")
    if kind != "upstream" and acquisition.fetched_urls:
        fail("acquisition.fetched_urls", f"must be empty for {kind} material")

    _check_publication(kind, evidence.publication, fail)
    _check_acceptance(kind, evidence.platform_acceptance, fail)
    _check_validation(evidence.local_validation, fail)


def _check_license(
    manifest: Manifest,
    has_license: bool,
    prefix: str,
    fail: Any,
) -> None:
    kind = manifest.kind
    if kind == "original":
        if has_license:
            fail("license", "must be null for original material")
        return
    record = manifest.license
    if record is None:
        fail("license", f"is required for {kind} material")
        return
    if record.identifier not in PERMISSIVE_LICENSES and not record.policy_note:
        fail(
            "license.policy_note",
            f"is required for the non-permissive license {record.identifier!r}: "
            "explain how its terms are honored",
        )
    notice_path = record.notice.path
    if kind == "upstream" and notice_path and not notice_path.startswith(prefix):
        fail("license.notice.path", f"must be under {prefix}")
    if kind == "adaptation" and notice_path and not notice_path.startswith("upstream/"):
        fail(
            "license.notice.path",
            "must point at the preserved notice under upstream/",
        )


def _check_publication(kind: str, publication: Publication, fail: Any) -> None:
    published = publication.status == "published"
    if kind == "upstream" and publication.status == "unpublished":
        fail("evidence.publication.status", "must be published for upstream material")
    if kind != "upstream" and published:
        fail(
            "evidence.publication.status",
            f"must be unpublished for {kind} material; only the upstream file "
            "was published",
        )
    parts = {
        "url": publication.url,
        "repository": publication.repository,
        "revision": publication.revision,
        "path": publication.path,
    }
    if published:
        for name, value in parts.items():
            if value is None:
                fail(f"evidence.publication.{name}", "is required when published")
        expected = (
            f"{publication.repository}/blob/{publication.revision}/{publication.path}"
        )
        if None not in parts.values() and publication.url != expected:
            fail("evidence.publication.url", f"must be {expected}")
    elif publication.status == "unpublished":
        for name, value in parts.items():
            if value is not None:
                fail(f"evidence.publication.{name}", "must be null when unpublished")


def _check_acceptance(kind: str, acceptance: PlatformAcceptance, fail: Any) -> None:
    if acceptance.status == "claimed_by_upstream" and kind != "upstream":
        fail(
            "evidence.platform_acceptance.status",
            "claimed_by_upstream applies only to the upstream file; changed or "
            "new code never inherits it",
        )
    if acceptance.status == "none":
        for name in ("platform", "evidence"):
            if getattr(acceptance, name) is not None:
                fail(
                    f"evidence.platform_acceptance.{name}",
                    "must be null when the status is none",
                )
    elif acceptance.status in PLATFORM_STATUSES:
        for name in ("platform", "evidence"):
            if getattr(acceptance, name) is None:
                fail(f"evidence.platform_acceptance.{name}", "is required for a claim")


def _check_validation(validation: LocalValidation, fail: Any) -> None:
    details = ("code_sha256", "run_at", "suite_sha256", "suite_version", "runner")
    if validation.status == "none":
        for name in details:
            if getattr(validation, name) is not None:
                fail(
                    f"evidence.local_validation.{name}",
                    "must be null when the status is none",
                )
    elif validation.status in VALIDATION_STATUSES:
        for name in ("code_sha256", "run_at", "runner"):
            if getattr(validation, name) is None:
                fail(
                    f"evidence.local_validation.{name}",
                    "is required: a result is bound to the code that produced it",
                )
