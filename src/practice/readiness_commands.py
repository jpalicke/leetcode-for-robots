# ABOUTME: Handler for `practice readiness`, which reports a package's readiness record.
# ABOUTME: Exit 0 when ready, 1 when not ready and 3 when the package cannot be loaded.

import argparse
import json
import sys
from pathlib import Path

from practice.exit_codes import EXIT_BAD_INPUT, EXIT_NOT_PASSED
from practice.paths import default_package_dir
from practice.readiness import ReadinessReport, check_readiness


def run_readiness_command(args: argparse.Namespace, references: Path) -> int:
    directory = args.package or default_package_dir(args.platform, args.problem_id)
    report = check_readiness(directory, references)
    if len(report.checks) == 1:  # Only a package that cannot load stops after one.
        print(f"practice: error: {report.checks[0].detail}", file=sys.stderr)
        return EXIT_BAD_INPUT
    if args.json:
        print(json.dumps(report.to_dict(), indent=2))
    else:
        print(_format(report, args.platform, args.problem_id))
    return 0 if report.ready else EXIT_NOT_PASSED


def _format(report: ReadinessReport, platform: str, problem_id: str) -> str:
    verdict = "READY" if report.ready else "NOT READY"
    lines = [f"{verdict}  {platform}/{problem_id}"]
    for check in report.checks:
        lines.append(
            f"  {'ok  ' if check.ok else 'FAIL'}  {check.name}: {check.detail}"
        )
    lines.append(f"platform acceptance: {report.platform_acceptance}")
    verification = report.record.get("verification", {})
    if verification:
        lines.append(
            f"verified on {verification.get('checked_on', 'an unknown date')}:"
        )
        lines += [f"  - {item['fact']}" for item in verification.get("verified", [])]
        lines.append("not verified:")
        lines += [f"  - {item}" for item in verification.get("not_verified", [])]
    return "\n".join(lines)
