# ABOUTME: Handlers for `practice sources`: add, add-local, validate, verify, list.
# ABOUTME: Source problems exit 3 and a missing source id exits 1, as elsewhere.

import argparse
import json
import sys
from pathlib import Path

from practice.exit_codes import EXIT_BAD_INPUT, EXIT_NOT_PASSED
from practice.sources import (
    LocalRequest,
    SourceError,
    SourceNotFoundError,
    UpstreamRequest,
    add_local,
    add_upstream,
    citation,
    list_source_ids,
    load_manifest,
    validate_source,
    verify_references,
)


def run_sources_command(args: argparse.Namespace, references: Path) -> int:
    try:
        return _dispatch(args, references)
    except SourceNotFoundError as error:
        print(f"practice: error: {error}", file=sys.stderr)
        return EXIT_NOT_PASSED
    except SourceError as error:
        print(f"practice: error: {error}", file=sys.stderr)
        return EXIT_BAD_INPUT


def _dispatch(args: argparse.Namespace, references: Path) -> int:
    handlers = {
        "add": _add,
        "add-local": _add_local,
        "validate": _validate,
        "verify": _verify,
        "show": _show,
        "list": _list,
    }
    return handlers[args.sources_command](args, references)


def _add(args: argparse.Namespace, references: Path) -> int:
    manifest = add_upstream(
        references,
        UpstreamRequest(
            source_id=args.source_id,
            repository=args.repository,
            revision=args.revision,
            path=args.path,
            license_path=args.license_path,
            license_identifier=args.license_id,
            license_terms=args.terms,
            policy_note=args.policy_note,
            language=args.language,
            classification=args.classification,
            title=args.title,
            raw_base=args.raw_base,
            actor=args.actor,
        ),
    )
    print(f"preserved {manifest.id}")
    print(f"  file    {manifest.file.path}  sha256 {manifest.file.sha256}")
    if manifest.license is not None:
        notice = manifest.license.notice
        print(f"  notice  {notice.path}  sha256 {notice.sha256}")
    print("  validation: none (intake does not run or vouch for the code)")
    return 0


def _add_local(args: argparse.Namespace, references: Path) -> int:
    manifest = add_local(
        references,
        LocalRequest(
            source_id=args.source_id,
            kind=args.kind,
            source_file=args.file,
            language=args.language,
            classification=args.classification,
            title=args.title,
            actor=args.actor,
            derived_from=args.derived_from,
            transformation=args.transformation,
        ),
    )
    print(f"registered {manifest.kind} {manifest.id}")
    print(f"  file    {manifest.file.path}  sha256 {manifest.file.sha256}")
    return 0


def _validate(args: argparse.Namespace, references: Path) -> int:
    manifest = validate_source(references, args.source_id, args.package, args.timeout)
    recorded = manifest.evidence.local_validation
    print(f"{manifest.id}: local validation {recorded.status}")
    print(f"  code sha256   {recorded.code_sha256}")
    print(f"  suite         {recorded.suite_version}  sha256 {recorded.suite_sha256}")
    print(f"  run at        {recorded.run_at}")
    print("  platform acceptance is a separate fact and was not touched")
    return 0 if recorded.status == "passed" else EXIT_NOT_PASSED


def _verify(args: argparse.Namespace, references: Path) -> int:
    report = verify_references(references)
    for source_id in report.verified:
        print(f"ok  {source_id}")
    for problem in report.problems:
        print(f"practice: error: {problem}", file=sys.stderr)
    if report.problems:
        print(
            f"{len(report.problems)} problem(s); {len(report.verified)} source(s) ok",
            file=sys.stderr,
        )
        return EXIT_BAD_INPUT
    print(f"{len(report.verified)} source(s) verified")
    return 0


def _show(args: argparse.Namespace, references: Path) -> int:
    cited = citation(references, args.source_id)
    if args.json:
        print(json.dumps(cited.to_dict(), indent=2, ensure_ascii=False))
        return 0
    lines = [
        f"{cited.id}  ({cited.kind})",
        f"title:          {cited.title}",
        f"language:       {cited.language}",
        f"classification: {cited.classification}"
        f"{' (spoiler)' if cited.spoiler else ''}",
        f"url:            {cited.url or 'none'}",
        f"revision:       {cited.revision or 'none'}",
        f"path:           {cited.path or 'none'}",
        f"license:        {cited.license_identifier or 'none'}",
        f"file:           {cited.file_path}",
        f"file sha256:    {cited.file_sha256}",
        f"notice sha256:  {cited.notice_sha256 or 'none'}",
        f"acquired at:    {cited.acquired_at}",
        f"platform acceptance: {cited.platform_acceptance}",
        f"local validation:    {cited.local_validation}",
    ]
    if cited.derived_from:
        lines.insert(1, f"derived from:   {cited.derived_from}")
    if cited.policy_note:
        lines.append(f"policy note:    {cited.policy_note}")
    print("\n".join(lines))
    return 0


def _list(args: argparse.Namespace, references: Path) -> int:
    ids = list_source_ids(references)
    if not ids:
        print("No sources have been imported.")
        return 0
    for source_id in ids:
        manifest = load_manifest(references, source_id)
        print(f"{source_id}  {manifest.kind}  {manifest.classification}")
    return 0
