# ABOUTME: Rebuilds catalog/leetcode-topics.json: each problem's category and topics.
# ABOUTME: Rate-limited, https only, no redirects; writes nothing if any check fails.

import argparse
import json
import os
import sys
import tempfile
import time
from datetime import date
from pathlib import Path
from typing import Any

from practice.catalog import Catalog, CatalogError, load_catalog
from practice.paths import REPO_ROOT
from practice.source_fetch import FetchError, address_refusal, fetch_url
from practice.topics import CATEGORIES, TopicsError, parse_topics

DEFAULT_CATALOG = REPO_ROOT / "catalog" / "leetcode.json"
DEFAULT_OUTPUT = REPO_ROOT / "catalog" / "leetcode-topics.json"
LEETCODE_URL = "https://leetcode.com/graphql"
SOURCE_URL = "https://leetcode.com/graphql"
MAX_PAGES = 500
QUERY = (
    "query q($categorySlug: String, $limit: Int, $skip: Int, "
    "$filters: QuestionListFilterInput) { problemsetQuestionList: "
    "questionList(categorySlug: $categorySlug, limit: $limit, skip: $skip, "
    "filters: $filters) { total: totalNum questions: data { "
    "frontendQuestionId: questionFrontendId titleSlug isPaidOnly difficulty "
    "topicTags { slug name } } } }"
)
NOTE = "Category and topic tag slugs only; no problem text."


class ToolError(Exception):
    """A fetch or consistency check failed; exit 1 and write nothing."""


class UsageError(Exception):
    """The command line asked for something not allowed; exit 2."""


class Fetcher:
    def __init__(self, url: str, delay: float, page_size: int) -> None:
        self.url = url
        self.delay = delay
        self.page_size = page_size
        self.last: float | None = None

    def _pause(self) -> None:
        if self.last is not None:
            remaining = self.delay - (time.monotonic() - self.last)
            if remaining > 0:
                time.sleep(remaining)
        self.last = time.monotonic()

    def _page(self, category: str, skip: int) -> tuple[int, list[dict[str, Any]]]:
        self._pause()
        body = json.dumps(
            {
                "query": QUERY,
                "variables": {
                    "categorySlug": category,
                    "skip": skip,
                    "limit": self.page_size,
                    "filters": {},
                },
            }
        ).encode()
        headers = {
            "Content-Type": "application/json",
            "Referer": "https://leetcode.com/problemset/",
            "User-Agent": "leetcode-for-robots topic refresh",
        }
        try:
            raw = fetch_url(self.url, data=body, headers=headers)
        except FetchError as error:
            raise ToolError(str(error)) from error
        try:
            payload = json.loads(raw)
        except (json.JSONDecodeError, UnicodeDecodeError) as error:
            raise ToolError(
                f"the response from {self.url} is not valid JSON: {error}"
            ) from error
        try:
            found = payload["data"]["problemsetQuestionList"]
            return int(found["total"]), list(found["questions"])
        except (KeyError, TypeError, ValueError) as error:
            raise ToolError(
                f"the list for category {category!r} came back in an unexpected "
                f"shape ({error!r})"
            ) from error

    def everything(self, category: str) -> list[dict[str, Any]]:
        """Every question of one category (or all of them when it is empty)."""
        collected: list[dict[str, Any]] = []
        total: int | None = None
        for _ in range(MAX_PAGES):
            page_total, page = self._page(category, len(collected))
            total = page_total if total is None else total
            collected.extend(page)
            if len(collected) >= total:
                return collected
            if not page:
                break
        raise ToolError(
            f"category {category!r}: LeetCode's total says {total} problems but "
            f"only {len(collected)} came back"
        )


def facts_from(fetcher: Fetcher, catalog: Catalog) -> dict[int, dict[str, list[str]]]:
    by_id = {entry.frontend_question_id: entry for entry in catalog.entries}
    everything = fetcher.everything("")
    topics: dict[int, list[str]] = {}
    try:
        for q in everything:
            number = int(q["frontendQuestionId"])
            entry = by_id.get(number)
            if entry is None:
                raise ToolError(f"problem {number} is not in the catalog")
            if q["titleSlug"] != entry.slug:
                raise ToolError(
                    f"problem {number} has slug {q['titleSlug']!r} on LeetCode but "
                    f"the catalog says {entry.slug!r}"
                )
            if bool(q["isPaidOnly"]) != entry.paid_only:
                says = "premium" if q["isPaidOnly"] else "free"
                raise ToolError(
                    f"problem {number}: LeetCode says {says} but the catalog "
                    f"disagrees about premium"
                )
            topics[number] = sorted({tag["slug"] for tag in q["topicTags"]})
    except (KeyError, TypeError, ValueError) as error:
        raise ToolError(
            f"a question came back in an unexpected shape ({error!r})"
        ) from error
    for number in sorted(set(by_id) - set(topics)):
        raise ToolError(f"problem {number} is missing from LeetCode's full list")
    members: dict[int, set[str]] = {number: set() for number in topics}
    for category in CATEGORIES:
        for q in fetcher.everything(category):
            try:
                number = int(q["frontendQuestionId"])
            except (KeyError, TypeError, ValueError) as error:
                raise ToolError(
                    f"a question in category {category!r} has no usable number"
                ) from error
            if number not in members:
                raise ToolError(
                    f"problem {number} (category {category!r}) is not in the full list"
                )
            members[number].add(category)
    for number in sorted(members):
        if not members[number]:
            raise ToolError(f"problem {number} is in no category")
    return {
        number: {"categories": sorted(members[number]), "topics": topics[number]}
        for number in sorted(topics)
    }


def build(facts: dict[int, dict[str, list[str]]], fetched_on: str) -> dict[str, Any]:
    return {
        "schema_version": 1,
        "platform": "leetcode",
        "source_url": SOURCE_URL,
        "fetched_on": fetched_on,
        "note": NOTE,
        "entries": [
            {"id": number, "categories": fact["categories"], "topics": fact["topics"]}
            for number, fact in sorted(facts.items())
        ],
    }


def render(data: dict[str, Any]) -> str:
    """One problem per line, so a changed tag shows up as a one-line diff."""
    head = {k: v for k, v in data.items() if k != "entries"}
    top = json.dumps(head, indent=2)[:-2] + ","
    rows = ",\n".join(
        f"    {json.dumps(e, separators=(', ', ': '))}" for e in data["entries"]
    )
    return f'{top}\n  "entries": [\n{rows}\n  ]\n}}\n'


def write_atomically(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    handle, temporary = tempfile.mkstemp(
        dir=path.parent, prefix=".topics-", suffix=".tmp"
    )
    try:
        with os.fdopen(handle, "w", encoding="utf-8", newline="\n") as stream:
            stream.write(text)
        os.replace(temporary, path)
    except BaseException:
        Path(temporary).unlink(missing_ok=True)
        raise


def run(args: argparse.Namespace) -> int:
    refusal = address_refusal(args.leetcode_url)
    if refusal:
        raise UsageError(f"--leetcode-url {args.leetcode_url}: {refusal}")
    try:
        catalog = load_catalog(args.catalog)
    except CatalogError as error:
        raise ToolError(str(error)) from error
    fetcher = Fetcher(args.leetcode_url, args.delay, args.page_size)
    data = build(facts_from(fetcher, catalog), args.fetched_on)
    try:
        parse_topics(data, catalog)
    except TopicsError as error:
        raise ToolError(str(error)) from error
    if args.check:
        return check(args.output, data)
    write_atomically(args.output, render(data))
    print(f"wrote facts for {len(data['entries'])} problems to {args.output}")
    return 0


def check(path: Path, fresh: dict[str, Any]) -> int:
    try:
        committed = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        print(f"{path} is missing or unreadable", file=sys.stderr)
        return 1
    committed.pop("fetched_on", None)
    expected = {k: v for k, v in fresh.items() if k != "fetched_on"}
    if committed != expected:
        print(f"{path} differs from LeetCode's current lists", file=sys.stderr)
        return 1
    print(f"the facts for {len(fresh['entries'])} problems match LeetCode's lists")
    return 0


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description="Refresh category and topic facts.")
    parser.add_argument("--catalog", type=Path, default=DEFAULT_CATALOG)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--leetcode-url", default=LEETCODE_URL)
    parser.add_argument(
        "--delay", type=float, default=1.5, help="seconds between requests"
    )
    parser.add_argument("--page-size", type=int, default=100)
    parser.add_argument("--fetched-on", default=date.today().isoformat())
    parser.add_argument("--check", action="store_true", help="compare, do not write")
    args = parser.parse_args(argv)
    if args.delay < 0 or args.page_size < 1:
        print(
            "fetch_catalog_topics.py: error: --delay and --page-size must be positive",
            file=sys.stderr,
        )
        return 2
    try:
        date.fromisoformat(args.fetched_on)
    except ValueError:
        print(
            "fetch_catalog_topics.py: error: --fetched-on must be an ISO date",
            file=sys.stderr,
        )
        return 2
    try:
        return run(args)
    except UsageError as error:
        print(f"fetch_catalog_topics.py: error: {error}", file=sys.stderr)
        return 2
    except ToolError as error:
        print(f"fetch_catalog_topics.py: error: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
