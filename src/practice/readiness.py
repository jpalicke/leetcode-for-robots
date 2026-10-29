# ABOUTME: Reports whether an exercise package meets its problem readiness criteria.
# ABOUTME: Each check reads real files and recorded evidence; nothing is trusted unseen.

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from practice.classification import ALL_CLASSES, is_spoiler
from practice.package import ExercisePackage, PackageError, load_package
from practice.source_manifest import Manifest, validation_state
from practice.sources import SourceError, load_manifest, verify_references
from practice.stubs import is_stub

RECORD_FILE = "readiness.json"
MIN_HINT_LEVELS = 4  # The tutor ladder runs from level 0 to level 3.
REFERENCE_GROUPS = ("upstream", "adaptations", "originals")
# Upstream code may not be runnable as stored; only local code must carry evidence.
VALIDATED_GROUPS = ("adaptations", "originals")
# Whether each listed file must be a spoiler class.
LISTED_FILES = {"statement": False, "notes": True}


@dataclass(frozen=True)
class Check:
    name: str
    ok: bool
    detail: str


@dataclass
class ReadinessReport:
    checks: list[Check] = field(default_factory=list)
    blockers: list[str] = field(default_factory=list)
    platform_acceptance: str = "none"
    record: dict[str, Any] = field(default_factory=dict)

    @property
    def ready(self) -> bool:
        return bool(self.checks) and all(check.ok for check in self.checks)

    def add(self, name: str, ok: bool, detail: str) -> None:
        self.checks.append(Check(name, ok, detail))

    def to_dict(self) -> dict[str, Any]:
        return {
            "ready": self.ready,
            "checks": [check.__dict__ for check in self.checks],
            "blockers": self.blockers,
            "platform_acceptance": self.platform_acceptance,
            "verification": self.record.get("verification", {}),
        }


def _read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def check_readiness(package_dir: Path, references: Path) -> ReadinessReport:
    report = ReadinessReport()
    try:
        package = load_package(package_dir)
    except PackageError as error:
        report.add("package", False, str(error))
        return report
    suite_size = len(package.suite.cases) if package.suite else 0
    report.add(
        "package",
        suite_size > 0,
        f"{package.platform}/{package.problem_id} loads with {suite_size} cases",
    )
    try:
        record = _read_json(package_dir / RECORD_FILE)
        if not isinstance(record, dict):
            raise ValueError("must hold a JSON object")
    except (OSError, ValueError) as error:
        report.add("record", False, f"{RECORD_FILE}: {error}")
        return report
    report.record = record
    same = (record.get("platform"), record.get("problem_id")) == (
        package.platform,
        package.problem_id,
    )
    report.add(
        "record",
        same,
        f"{RECORD_FILE} describes {record.get('platform')}/{record.get('problem_id')}",
    )
    _check_starter(report, package, package_dir)
    _check_files(report, record, package_dir)
    _check_hints(report, record, package_dir)
    _check_references(report, record, references, package)
    report.blockers = [str(item) for item in record.get("blockers", [])]
    report.add(
        "blockers",
        not report.blockers,
        "; ".join(report.blockers) or "no blockers",
    )
    return report


def _check_starter(
    report: ReadinessReport, package: ExercisePackage, directory: Path
) -> None:
    try:
        source = (directory / "starter.py").read_text(encoding="utf-8")
    except OSError as error:
        report.add("starter", False, f"cannot read starter.py: {error}")
        return
    stub = is_stub(source, package.function_name, allow_none=package.allow_none)
    report.add("starter", stub, f"starter.py leaves {package.function_name} a stub")


def _check_files(
    report: ReadinessReport, record: dict[str, Any], directory: Path
) -> None:
    problems: list[str] = []
    for key, must_hide in LISTED_FILES.items():
        entry = record.get("files", {}).get(key)
        if not isinstance(entry, dict):
            problems.append(f"{key} is not listed")
            continue
        name = str(entry.get("content_class"))
        if name not in ALL_CLASSES:
            problems.append(f"{key} has unknown content class {name!r}")
        elif is_spoiler(name) != must_hide:
            problems.append(f"{key} is classed {name!r}, which has the wrong status")
        if not (directory / str(entry.get("path"))).is_file():
            problems.append(f"{key} file {entry.get('path')!r} is missing")
    report.add("files", not problems, "; ".join(problems) or "statement and notes ok")


def _check_hints(
    report: ReadinessReport, record: dict[str, Any], directory: Path
) -> None:
    try:
        index = _read_json(directory / str(record.get("files", {}).get("hints")))
        hints = index["hints"]
        if not isinstance(hints, list):
            raise TypeError("hints must be a list")
    except (OSError, ValueError, KeyError, TypeError) as error:
        report.add("hints", False, f"hint index unreadable: {error}")
        return
    problems: list[str] = []
    if len(hints) < MIN_HINT_LEVELS:
        problems.append(f"{len(hints)} levels, at least {MIN_HINT_LEVELS} needed")
    for position, hint in enumerate(hints):
        if not isinstance(hint, dict):
            problems.append(f"entry {position} is not an object")
            continue
        name = str(hint.get("content_class"))
        if hint.get("level") != position:
            problems.append(f"entry {position} has level {hint.get('level')!r}")
        if name not in ALL_CLASSES:
            problems.append(f"level {position}: unknown class {name!r}")
        elif hint.get("spoiler") is not is_spoiler(name):
            problems.append(f"level {position}: spoiler flag disagrees with {name!r}")
        if not (directory / "hints" / str(hint.get("file"))).is_file():
            problems.append(f"level {position}: file {hint.get('file')!r} is missing")
        if hint.get("names_technique") and position < len(hints) - 1:
            problems.append(f"level {position} names the technique before the last")
    last = hints[-1] if hints else None
    if isinstance(last, dict) and not last.get("names_technique"):
        problems.append("the last level should be the one that names the technique")
    report.add("hints", not problems, "; ".join(problems) or f"{len(hints)} levels ok")


def _load(references: Path, source: str) -> Manifest | None:
    try:
        return load_manifest(references, source)
    except SourceError:
        return None


def _check_references(
    report: ReadinessReport,
    record: dict[str, Any],
    references: Path,
    package: ExercisePackage,
) -> None:
    listed: dict[str, list[str]] = {
        group: [str(i) for i in record.get("references", {}).get(group, [])]
        for group in REFERENCE_GROUPS
    }
    ids = [source for group in REFERENCE_GROUPS for source in listed[group]]
    problems: list[str] = []
    if not listed["upstream"]:
        problems.append("no upstream reference is listed")
    if not listed["originals"]:
        problems.append("no original reference is listed")
    found = verify_references(references).problems
    for source in ids:
        if _load(references, source) is None:
            problems.append(f"{source}: no such source")
        problems += [p for p in found if p.startswith(f"{source}:")]
    report.add("references", not problems, "; ".join(problems) or f"{len(ids)} ok")

    stale: list[str] = []
    for group in VALIDATED_GROUPS:
        for source in listed[group]:
            manifest = _load(references, source)
            if manifest is None:
                continue  # Already reported by the references check.
            local = manifest.evidence.local_validation
            state = validation_state(manifest)
            if state != "current" or local.status != "passed":
                stale.append(f"{source}: validation is {state}, {local.status}")
            elif local.suite_sha256 != package.suite_sha256:
                stale.append(f"{source}: validated against a different suite")
    report.add("evidence", not stale, "; ".join(stale) or "current on this suite")

    manifests = [m for m in (_load(references, s) for s in ids) if m is not None]
    accepted = {m.evidence.platform_acceptance.status for m in manifests}
    report.platform_acceptance = "none" if accepted <= {"none"} else "recorded"
