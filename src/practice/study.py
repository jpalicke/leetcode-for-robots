# ABOUTME: Study units: the cited concept sources a problem lists, and the handoff text.
# ABOUTME: Reads readiness.json and source manifests only; it writes nothing.

import json
from dataclasses import dataclass
from pathlib import Path

from practice.sources import SourceError, citation

STUDY_REMINDER = (
    "Study mode explains concepts only. It never authorizes the full solution, "
    "and practice mode stays closed to these units unless you ask for them."
)


class StudyError(Exception):
    """A problem's study units cannot be read or cited, so none are offered."""


@dataclass(frozen=True)
class StudyUnit:
    source_id: str
    title: str
    url: str | None
    revision: str | None
    license_identifier: str | None
    license_terms: str | None


def study_units(
    references: Path, problems_dir: Path, platform: str, problem_id: str
) -> tuple[StudyUnit, ...]:
    """The cited study units a problem lists, or none when it lists none."""
    readiness = problems_dir / f"{platform}-{problem_id}" / "readiness.json"
    if not readiness.is_file():
        return ()
    try:
        record = json.loads(readiness.read_text(encoding="utf-8"))
    except (OSError, ValueError) as error:
        raise StudyError(f"cannot read {readiness}: {error}") from error
    ids = record.get("knowledge_sources", []) if isinstance(record, dict) else []
    if not isinstance(ids, list) or not all(isinstance(i, str) for i in ids):
        raise StudyError(f"{readiness}: knowledge_sources must be a list of source IDs")
    units: list[StudyUnit] = []
    for source_id in ids:
        try:
            cited = citation(references, source_id)
        except SourceError as error:
            raise StudyError(str(error)) from error
        units.append(
            StudyUnit(
                source_id,
                cited.title,
                cited.url,
                cited.revision,
                cited.license_identifier,
                cited.license_terms,
            )
        )
    return tuple(units)


def export_command(platform: str, problem_id: str, unit: StudyUnit) -> str:
    return (
        f"practice knowledge export {platform} {problem_id} "
        f"--mode study --source {unit.source_id}"
    )


def handoff(platform: str, problem_id: str, units: tuple[StudyUnit, ...]) -> str:
    """What the learner gives the tutor: exports to run, a request, and the terms."""
    lines = ["Study material for the tutor (you chose study mode for this attempt):"]
    lines.extend(f"  {export_command(platform, problem_id, u)}" for u in units)
    names = ", ".join(u.title for u in units)
    lines.append("Paste-ready request for the tutor:")
    lines.append(
        f"  I chose study mode for {platform} {problem_id}. Please run the export "
        f"commands above and teach me the concept from: {names}. "
        "Do not give me the full solution."
    )
    lines.append("Sources and terms:")
    for unit in units:
        revision = unit.revision or "unpinned"
        lines.append(f"  {unit.title}: {unit.url} (revision {revision})")
        lines.append(f"    License {unit.license_identifier}: {unit.license_terms}")
    lines.append(STUDY_REMINDER)
    return "\n".join(lines)
