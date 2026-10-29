# ABOUTME: Handler for `practice request`, which prepares a paste-ready tutor request.
# ABOUTME: It prints and saves the request; it never records help or sends anything.

import argparse
import sys
from pathlib import Path

from practice.exit_codes import EXIT_BAD_INPUT, EXIT_USAGE
from practice.history import AttemptError
from practice.journal import JournalError
from practice.package import PackageError
from practice.tutor_request import RequestError, prepare_request


def run_request_command(args: argparse.Namespace, practice_dir: Path) -> int:
    try:
        prepared = prepare_request(
            practice_dir,
            args.attempt_id,
            args.package,
            action=args.action,
            mode=args.mode,
            timed=args.timed,
            reveal=args.reveal,
        )
    except (AttemptError, RequestError) as error:
        print(f"practice: error: {error}", file=sys.stderr)
        return EXIT_USAGE
    except (PackageError, JournalError) as error:
        print(f"practice: error: {error}", file=sys.stderr)
        return EXIT_BAD_INPUT
    for notice in prepared.notices:
        print(f"practice: warning: {notice}", file=sys.stderr)
    sys.stdout.write(prepared.text)
    print(
        f"Saved to {prepared.path}. Nothing was sent and nothing was recorded; "
        "paste the request into your tutor chat yourself.",
        file=sys.stderr,
    )
    return 0
