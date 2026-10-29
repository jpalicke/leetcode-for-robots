# ABOUTME: Exports explicitly selected public knowledge after metadata privacy checks.
# ABOUTME: Produces portable deterministic JSON chunks with verified source provenance.

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

from practice.classification import CONTENT_CLASSES, LEARNER_CLASSES
from practice.source_manifest import Manifest, sha256_hex
from practice.sources import SourceError, citation, load_manifest

CHUNK_SIZE = 2000
_IDENTITY = re.compile(r"[a-zA-Z0-9][a-zA-Z0-9_-]*")


class KnowledgeError(Exception):
    """The selected public material or export request is invalid."""


def _public(path: Path, private: Path) -> Path:
    resolved = path.resolve()
    if any(
        part.lower() in {".practice", *LEARNER_CLASSES}
        for part in (*path.parts, *resolved.parts)
    ):
        raise KnowledgeError("private content paths cannot be exported")
    if resolved.is_relative_to(private.resolve()):
        raise KnowledgeError("private practice directory cannot be exported")
    return resolved


def _safe(root: Path, name: object, private: Path) -> Path:
    if not isinstance(name, str) or not name or "\\" in name or ":" in name:
        raise KnowledgeError("content path must be a safe relative path")
    if name.startswith("/") or any(p in ("", ".", "..") for p in name.split("/")):
        raise KnowledgeError("content path must be a safe relative path")
    target = _public(root / name, private)
    if not target.is_relative_to(root.resolve()):
        raise KnowledgeError("content path escapes its input directory")
    return target


def _object(path: Path) -> dict[str, Any]:
    data: object = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise KnowledgeError(f"{path.name} must contain an object")
    return data


def _class(name: object) -> str:
    if not isinstance(name, str) or name in LEARNER_CLASSES or name == "test_data":
        raise KnowledgeError("private learner content and test_data cannot be exported")
    if name not in CONTENT_CLASSES:
        raise KnowledgeError(f"unknown content class {name!r}")
    return name


def _document(
    platform: str,
    problem_id: str,
    language: str,
    role: str,
    kind: str,
    raw: bytes,
    reveal: str,
    *,
    source: str | None = None,
    provenance: dict[str, Any] | None = None,
    notice: str | None = None,
) -> dict[str, Any]:
    identity = "/".join((platform, problem_id, language, role, source or "project"))
    document_id = "document-" + sha256_hex(identity.encode("utf-8"))
    text = raw.decode("utf-8")
    chunks: list[dict[str, Any]] = []
    offset = 0
    while offset < len(text):
        end = min(offset + CHUNK_SIZE, len(text))
        if end < len(text):
            boundary = text.rfind("\n", offset, end)
            if boundary > offset:
                end = boundary + 1
        block = text[offset:end]
        ordinal = len(chunks)
        chunks.append(
            {
                "id": f"{document_id}/chunk-{ordinal:06d}",
                "ordinal": ordinal,
                "content_sha256": sha256_hex(block.encode("utf-8")),
                "text": block,
            }
        )
        offset = end
    return {
        "id": document_id,
        "platform": platform,
        "problem_id": problem_id,
        "language": language,
        "role": role,
        "source_id": source,
        "content_kind": kind,
        "reveal": reveal,
        "revision": provenance.get("revision") if provenance else None,
        "source_sha256": sha256_hex(raw),
        "content_sha256": sha256_hex(raw),
        "citation": provenance,
        "notice": notice,
        "provenance": "registered_source" if source else "project_authored",
        "chunks": chunks,
    }


def _source_paths(references: Path, manifest: Manifest, private: Path) -> None:
    _safe(references, manifest.file.path, private)
    if manifest.license:
        _safe(references, manifest.license.notice.path, private)


def export_knowledge(
    problems: Path,
    references: Path,
    private: Path,
    platform: str,
    problem_id: str,
    *,
    language: str = "python",
    mode: str = "practice",
    hint_level: int | None = None,
    reveal_solution: bool = False,
    source_ids: tuple[str, ...] = (),
) -> str:
    """Select by metadata first; never discover or read private learner material."""
    try:
        return _export(
            problems,
            references,
            private,
            platform,
            problem_id,
            language,
            mode,
            hint_level,
            reveal_solution,
            source_ids,
        )
    except (OSError, UnicodeError, ValueError, SourceError) as error:
        # Do not include OSError's machine-specific path or source contents.
        if isinstance(error, OSError):
            raise KnowledgeError("cannot read selected input file") from error
        raise KnowledgeError(str(error)) from error


def _export(
    problems: Path,
    references: Path,
    private: Path,
    platform: str,
    problem_id: str,
    language: str,
    mode: str,
    hint_level: int | None,
    reveal_solution: bool,
    source_ids: tuple[str, ...],
) -> str:
    if not all(_IDENTITY.fullmatch(s) for s in (platform, problem_id, language)):
        raise KnowledgeError(
            "platform, problem ID and language must be simple identifiers"
        )
    if mode not in ("practice", "study"):
        raise KnowledgeError("mode must be practice or study")
    if hint_level is not None and (
        type(hint_level) is not int or hint_level < 0 or reveal_solution
    ):
        raise KnowledgeError("choose a nonnegative hint level or full solution reveal")
    root = _public(problems, private)
    package = _safe(root, f"{platform}-{problem_id}", private)
    metadata = _object(_safe(package, "problem.json", private))
    record = _object(_safe(package, "readiness.json", private))
    if (metadata.get("platform"), metadata.get("id"), metadata.get("language")) != (
        platform,
        problem_id,
        language,
    ):
        raise KnowledgeError(
            "problem metadata does not match requested problem/language"
        )
    if record.get("schema_version") != 1 or (
        record.get("platform"),
        record.get("problem_id"),
        record.get("language"),
    ) != (platform, problem_id, language):
        raise KnowledgeError(
            "readiness metadata does not match requested problem/language"
        )
    files = record.get("files")
    if not isinstance(files, dict):
        raise KnowledgeError("readiness files must be an object")
    # The selected list contains metadata only. Assemble no body until it is complete.
    selected: list[tuple[str, str, Path, str]] = []
    for role in ("statement", "notes") if reveal_solution else ("statement",):
        entry = files.get(role)
        if not isinstance(entry, dict):
            raise KnowledgeError(f"{role} metadata is missing")
        kind = _class(entry.get("content_class"))
        expected = (
            ("statement_summary",) if role == "statement" else ("reference_solution",)
        )
        if kind not in expected:
            raise KnowledgeError(f"{role} has an inappropriate content class")
        selected.append(
            (
                role,
                kind,
                _safe(package, entry.get("path"), private),
                "solution" if role == "notes" else "default",
            )
        )
    if hint_level is not None:
        index_path = _safe(package, files.get("hints"), private)
        index = _object(index_path)
        hints = index.get("hints")
        if not isinstance(hints, list):
            raise KnowledgeError("hint index must contain a hints list")
        matches = [
            h
            for h in hints
            if isinstance(h, dict)
            and type(h.get("level")) is int
            and h.get("level") == hint_level
        ]
        if len(matches) != 1:
            raise KnowledgeError("requested hint level must occur exactly once")
        hint = matches[0]
        if (
            _class(hint.get("content_class")) != "hint"
            or hint.get("spoiler") is not True
        ):
            raise KnowledgeError("selected hint classification is invalid")
        selected.append(
            (
                f"hint-{hint_level}",
                "hint",
                _safe(index_path.parent, hint.get("file"), private),
                f"hint-{hint_level}",
            )
        )
    sources: list[Manifest] = []
    if source_ids:
        groups = record.get("references", {})
        extra = record.get("knowledge_sources", [])
        if not isinstance(groups, dict) or not isinstance(extra, list):
            raise KnowledgeError("source associations must be lists")
        associated: list[str] = []
        for group in ("upstream", "adaptations", "originals"):
            ids = groups.get(group, [])
            if not isinstance(ids, list) or not all(isinstance(s, str) for s in ids):
                raise KnowledgeError("source associations must be lists of source IDs")
            associated.extend(ids)
        if not all(isinstance(s, str) for s in extra):
            raise KnowledgeError("knowledge_sources must be a list of source IDs")
        associated.extend(extra)
        for source_id in sorted(set(source_ids)):
            if source_id not in associated:
                raise KnowledgeError(
                    f"source {source_id!r} is not associated with this problem"
                )
            _safe(references, f"manifests/{source_id}.json", private)
            manifest = load_manifest(references, source_id)
            if manifest.id != source_id or manifest.language != language:
                raise KnowledgeError(
                    "source metadata does not match requested source/language"
                )
            kind = _class(manifest.classification)
            prose = Path(manifest.file.path).suffix.lower() in (".md", ".txt", ".rst")
            allowed = (
                (kind == "statement_summary" and prose)
                or (kind == "teaching_explanation" and mode == "study" and prose)
                or (
                    reveal_solution
                    and kind in ("reference_solution", "algorithm_implementation")
                )
            )
            if not allowed:
                raise KnowledgeError(
                    f"source {source_id!r} is excluded by the selected reveal scope"
                )
            _source_paths(references, manifest, private)
            if manifest.derived_from:
                _safe(references, f"manifests/{manifest.derived_from}.json", private)
                upstream = load_manifest(references, manifest.derived_from)
                if upstream.id != manifest.derived_from or upstream.kind != "upstream":
                    raise KnowledgeError(
                        "lineage must name the matching upstream entry"
                    )
                _source_paths(references, upstream, private)
            sources.append(manifest)
    documents = [
        _document(platform, problem_id, language, role, kind, path.read_bytes(), reveal)
        for role, kind, path, reveal in selected
    ]
    for manifest in sources:
        # citation verifies selected bytes, license notice and adaptation lineage.
        if manifest.derived_from:
            citation(references, manifest.derived_from)
        provenance = citation(references, manifest.id).to_dict()
        notice = (
            (references / manifest.license.notice.path).read_bytes().decode("utf-8")
            if manifest.license
            else None
        )
        documents.append(
            _document(
                platform,
                problem_id,
                language,
                "source",
                manifest.classification,
                (references / manifest.file.path).read_bytes(),
                "solution" if reveal_solution else mode,
                source=manifest.id,
                provenance=provenance,
                notice=notice,
            )
        )
    return (
        json.dumps(
            {"schema_version": 1, "chunk_size": CHUNK_SIZE, "documents": documents},
            ensure_ascii=False,
            sort_keys=True,
            indent=2,
        )
        + "\n"
    )


def run_knowledge_command(args: argparse.Namespace, private: Path) -> int:
    try:
        body = export_knowledge(
            args.problems_dir,
            args.references,
            private,
            args.platform,
            args.problem_id,
            language=args.language,
            mode=args.mode,
            hint_level=args.hint_level,
            reveal_solution=args.reveal_solution,
            source_ids=tuple(args.source),
        )
        if args.output is None:
            print(body, end="")
        else:
            output = _public(args.output, private)
            if any(
                output.is_relative_to(root.resolve())
                for root in (args.problems_dir, args.references)
            ):
                raise KnowledgeError(
                    "output must be outside protected input directories"
                )
            with output.open("x", encoding="utf-8", newline="\n") as stream:
                stream.write(body)
    except (KnowledgeError, OSError) as error:
        message = (
            "cannot create output; choose an unused writable path"
            if isinstance(error, OSError)
            else str(error)
        )
        print(f"practice: error: {message}", file=sys.stderr)
        return 3
    return 0
