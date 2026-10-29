# ABOUTME: Exposes catalog refresh with stable JSON and concise human reports.
# ABOUTME: Reports validation and acquisition failures without a traceback.

import argparse
import json
import sys
from datetime import date

from practice.catalog import CatalogError, load_catalog
from practice.catalog_refresh import refresh_catalog
from practice.exit_codes import EXIT_BAD_INPUT


def run_catalog_command(args: argparse.Namespace) -> int:
    try:
        report = refresh_catalog(args.catalog, args.source)
    except CatalogError as error:
        try:
            previous = load_catalog(args.catalog)
            age = (date.today() - date.fromisoformat(previous.fetched_on)).days
            age_message = f"Snapshot fetched_on {previous.fetched_on} ({age} days old)."
        except (CatalogError, ValueError, RecursionError):
            age_message = "Snapshot age unavailable because it cannot be validated."
        message = f"{error}. {age_message}"
        if args.json:
            print(json.dumps({"ok": False, "error": message}, sort_keys=True))
        else:
            print(f"practice: error: {message}", file=sys.stderr)
        return EXIT_BAD_INPUT
    if args.json:
        print(json.dumps({"ok": True, **report}, sort_keys=True))
    else:
        print(
            f"Catalog refreshed: {len(report['added'])} added, "
            f"{len(report['changed'])} changed, {len(report['removed'])} removed."
        )
        for kind in ("added", "changed", "removed"):
            for change in report[kind]:
                print(f"{kind}: {json.dumps(change, sort_keys=True)}")
        print(
            f"Coverage mapping #15: {len(report['pending_coverage'])} "
            "pending identities."
        )
    return 0
