# ABOUTME: Creates GitHub issues for catalog/ticket-plan.json and links them under #1.
# ABOUTME: Dry run by default; --apply writes. Duplicate-safe, resumable, rate-limited.

import argparse
import json
import os
import sys
import time
from pathlib import Path
from typing import Any

from practice.paths import REPO_ROOT
from practice.source_fetch import FetchError, address_refusal, fetch_url

# The tools run isolated (python -I), so reach the planner through the repository root.
sys.path.insert(0, str(REPO_ROOT))

from tools.plan_catalog import (  # noqa: E402
    Inputs,
    Outcome,
    Ticket,
    ToolError,
    load_inputs,
    read_plan,
    render_body,
    render_plan,
    write_atomically,
)

API_URL = "https://api.github.com"
DEFAULT_REPO = "jpalicke/leetcode-for-robots"
PAGE_SIZE = 100
MAX_PAGES = 50
MAX_RESPONSE_BYTES = 8 * 1024 * 1024


class UsageError(Exception):
    """The command line asked for something not allowed; exit 2."""


class GitHub:
    def __init__(self, api: str, repo: str, token: str | None, delay: float) -> None:
        self.api = api.rstrip("/")
        self.repo = repo
        self.token = token
        self.delay = delay
        self.last: float | None = None
        self.requests = 0
        self.known: list[dict[str, Any]] | None = None

    def _pause(self) -> None:
        if self.last is not None:
            remaining = self.delay - (time.monotonic() - self.last)
            if remaining > 0:
                time.sleep(remaining)

    def call(self, path: str, body: dict[str, Any] | None = None) -> Any:
        self._pause()
        self.requests += 1
        headers = {
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        }
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        data = None
        if body is not None:
            data = json.dumps(body).encode()
            headers["Content-Type"] = "application/json"
        url = f"{self.api}{path}"
        try:
            raw = fetch_url(
                url, max_bytes=MAX_RESPONSE_BYTES, data=data, headers=headers
            )
            return json.loads(raw)
        except FetchError as error:
            raise ToolError(str(error)) from error
        except ValueError as error:
            raise ToolError(f"{url} did not answer with JSON ({error})") from error
        finally:
            # Wait after a response so transport and server scheduling cannot
            # shorten the configured interval between observed requests.
            self.last = time.monotonic()

    def all_issues(self) -> list[dict[str, Any]]:
        """Every issue in the repository, open or closed, pull requests left out."""
        if self.known is None:
            found: list[dict[str, Any]] = []
            for page in range(1, MAX_PAGES + 1):
                batch = self.call(
                    f"/repos/{self.repo}/issues?state=all&per_page={PAGE_SIZE}"
                    f"&page={page}"
                )
                if not isinstance(batch, list):
                    raise ToolError("the issue list answered with an unexpected shape")
                found += [
                    i for i in batch if isinstance(i, dict) and "pull_request" not in i
                ]
                if len(batch) < PAGE_SIZE:
                    break
            else:
                raise ToolError(f"more than {MAX_PAGES * PAGE_SIZE} issues to list")
            self.known = found
        return self.known

    def find_by_title(self, title: str) -> list[dict[str, Any]]:
        """Issues whose title is exactly `title`."""
        return [i for i in self.all_issues() if i.get("title") == title]

    def create(self, title: str, body: str) -> dict[str, Any]:
        made = self.call(f"/repos/{self.repo}/issues", {"title": title, "body": body})
        if not isinstance(made, dict) or "number" not in made or "id" not in made:
            raise ToolError(f"creating {title!r} answered with an unexpected shape")
        self.all_issues().append(made)
        return made

    def linked(self, parent: int) -> set[int]:
        """Issue numbers already sub-issues of `parent`."""
        numbers: set[int] = set()
        for page in range(1, MAX_PAGES + 1):
            batch = self.call(
                f"/repos/{self.repo}/issues/{parent}/sub_issues"
                f"?per_page={PAGE_SIZE}&page={page}"
            )
            if not isinstance(batch, list):
                raise ToolError("the sub-issue list answered with an unexpected shape")
            numbers.update(int(i["number"]) for i in batch)
            if len(batch) < PAGE_SIZE:
                return numbers
        raise ToolError(f"#{parent} has more than {MAX_PAGES * PAGE_SIZE} sub-issues")

    def link(self, parent: int, issue_id: int) -> None:
        self.call(
            f"/repos/{self.repo}/issues/{parent}/sub_issues",
            {"sub_issue_id": issue_id},
        )

    def issue_id(self, number: int) -> int:
        issue = self.call(f"/repos/{self.repo}/issues/{number}")
        if not isinstance(issue, dict) or "id" not in issue:
            raise ToolError(f"issue #{number} answered with an unexpected shape")
        return int(issue["id"])


def body_of(ticket: Ticket, inputs: Inputs) -> str:
    text = render_body(ticket, inputs)
    _, _, rest = text.partition("\n\n")  # Drop the "# title" line; GitHub shows it.
    return rest


def run(args: argparse.Namespace) -> int:
    inputs = load_inputs(args)
    if not args.plan.exists():
        raise ToolError(f"there is no plan at {args.plan}; run plan_catalog.py first")
    tickets = read_plan(args.plan)
    token = os.environ.get("GITHUB_TOKEN") or None
    if args.apply and token is None:
        raise UsageError("--apply needs a GitHub token in the GITHUB_TOKEN variable")
    refusal = address_refusal(args.api_url)
    if refusal:
        raise UsageError(f"{args.api_url}: {refusal}")
    github = GitHub(args.api_url, args.repo, token, args.delay)
    verb = "" if args.apply else "would "
    created = adopted = linked_count = 0
    ids: dict[str, int] = {}
    # Create or adopt first, saving the plan after every ticket so a crash resumes.
    for ticket in tickets:
        if ticket.kind != "class" or ticket.issue is not None:
            continue
        matches = github.find_by_title(ticket.title)
        if len(matches) > 1:
            numbers = ", ".join(f"#{m['number']}" for m in matches)
            raise ToolError(
                f"{ticket.title!r} matches several issues ({numbers}); close the "
                "extras or put the right number in the plan by hand"
            )
        if matches:
            ticket.issue = int(matches[0]["number"])
            ids[ticket.ticket_id] = int(matches[0]["id"])
            adopted += 1
            print(f"{verb}adopt #{ticket.issue} for {ticket.ticket_id}: {ticket.title}")
        else:
            created += 1
            if not args.apply:
                print(f"would create {ticket.ticket_id}: {ticket.title}")
                continue
            made = github.create(ticket.title, body_of(ticket, inputs))
            ticket.issue = int(made["number"])
            ids[ticket.ticket_id] = int(made["id"])
            print(f"created #{ticket.issue} for {ticket.ticket_id}: {ticket.title}")
        if args.apply:
            write_atomically(args.plan, render_plan(Outcome(tickets), inputs))
    # Link every class ticket that has an issue and is not yet under the parent.
    already = github.linked(args.parent)
    for ticket in tickets:
        if ticket.kind != "class" or ticket.issue is None:
            continue
        if ticket.issue in already:
            continue
        linked_count += 1
        if not args.apply:
            print(f"would link #{ticket.issue} under #{args.parent}")
            continue
        issue_id = ids.get(ticket.ticket_id) or github.issue_id(ticket.issue)
        github.link(args.parent, issue_id)
        print(f"linked #{ticket.issue} under #{args.parent}")
    mode = "applied" if args.apply else "dry run, nothing written"
    print(
        f"{mode}: {verb}create {created}, {verb}adopt {adopted}, "
        f"{verb}link {linked_count}"
    )
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Create GitHub issues for the planned catalog tickets."
    )
    default = REPO_ROOT / "catalog"
    parser.add_argument("--catalog", type=Path, default=default / "leetcode.json")
    parser.add_argument("--topics", type=Path, default=default / "leetcode-topics.json")
    parser.add_argument("--rules", type=Path, default=default / "class-rules.json")
    parser.add_argument(
        "--curriculum", type=Path, default=REPO_ROOT / "curriculum" / "core.json"
    )
    parser.add_argument("--plan", type=Path, default=default / "ticket-plan.json")
    parser.add_argument("--repo", default=DEFAULT_REPO, help="OWNER/REPO")
    parser.add_argument("--api-url", default=API_URL)
    parser.add_argument("--parent", type=int, default=1, help="parent issue number")
    parser.add_argument(
        "--delay", type=float, default=2.0, help="seconds between GitHub requests"
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="create and link for real (the default is a read-only dry run)",
    )
    return parser


def main(argv: list[str]) -> int:
    args = build_parser().parse_args(argv)
    try:
        return run(args)
    except UsageError as error:
        print(f"tools/create_catalog_tickets.py: usage: {error}", file=sys.stderr)
        return 2
    except ToolError as error:
        print(f"tools/create_catalog_tickets.py: error: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
