# ABOUTME: Rebuilds catalog/lists/*.json from LeetCode study plans and NeetCode data.
# ABOUTME: Rate-limited, https only, no redirects, size-capped; never a partial set.

import argparse
import json
import os
import re
import sys
import tempfile
import time
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any

from practice.catalog import Catalog, CatalogError, load_catalog
from practice.lists import ListError, parse_list
from practice.paths import REPO_ROOT
from practice.source_fetch import FetchError, address_refusal, fetch_url

DEFAULT_REGISTRY = REPO_ROOT / "catalog" / "list-sources.json"
DEFAULT_CATALOG = REPO_ROOT / "catalog" / "leetcode.json"
DEFAULT_OUTPUT = REPO_ROOT / "catalog" / "lists"
LEETCODE_URL = "https://leetcode.com/graphql"
STUDY_PLAN_PAGE = "https://leetcode.com/studyplan/"
PLAN_KIND = "leetcode_study_plan"
SITE_KIND = "neetcode_site_data"
ALL_ROWS = "*"
QUERY = (
    "query q($slug: String!) { studyPlanV2Detail(planSlug: $slug) { slug name "
    "planSubGroups { name slug questions { titleSlug title questionFrontendId "
    "paidOnly } } } }"
)
NOTE = "Problem ids and slugs only; no problem text is stored."
SLUG = re.compile(r"[a-z0-9]+(-[a-z0-9]+)*")
REGISTRY_KEYS = {"schema_version", "site_data", "lists"}
SITE_KEYS = {"repository", "revision", "path", "license"}
LIST_KEYS = {"id", "name", "kind", "plan_slug", "flag", "size"}


class ToolError(Exception):
    """A fetch or validation failed; exit 1 and write nothing."""


class UsageError(Exception):
    """The command line asked for something not allowed; exit 2."""


@dataclass(frozen=True)
class SiteData:
    repository: str
    revision: str
    path: str
    license: str

    @property
    def raw_url(self) -> str:
        host = self.repository.replace("https://github.com/", "")
        return f"https://raw.githubusercontent.com/{host}/{self.revision}/{self.path}"

    @property
    def page_url(self) -> str:
        return f"{self.repository}/blob/{self.revision}/{self.path}"


@dataclass(frozen=True)
class ListSpec:
    list_id: str
    name: str
    kind: str
    reference: str  # The study plan slug or the site data flag.
    size: int

    def to_dict(self) -> dict[str, Any]:
        key = "plan_slug" if self.kind == PLAN_KIND else "flag"
        return {
            "id": self.list_id,
            "name": self.name,
            "kind": self.kind,
            key: self.reference,
            "size": self.size,
        }


Groups = list[tuple[str, list[tuple[int, str]]]]


def check_address(url: str, what: str) -> None:
    refusal = address_refusal(url)
    if refusal:
        raise UsageError(f"{what} {url}: {refusal}")


def read_url(url: str, body: bytes | None, headers: dict[str, str]) -> bytes:
    try:
        return fetch_url(url, data=body, headers=headers)
    except FetchError as error:
        raise ToolError(str(error)) from error


def parse_json(data: bytes, url: str) -> Any:
    try:
        return json.loads(data)
    except (json.JSONDecodeError, UnicodeDecodeError) as error:
        raise ToolError(
            f"the response from {url} is not valid JSON: {error}"
        ) from error


class Pacer:
    """Keeps at least `delay` seconds between requests to one host."""

    def __init__(self, delay: float) -> None:
        self.delay = delay
        self.last: float | None = None

    def wait(self) -> None:
        if self.last is not None:
            remaining = self.delay - (time.monotonic() - self.last)
            if remaining > 0:
                time.sleep(remaining)
        self.last = time.monotonic()


def fetch_plan(url: str, slug: str, pacer: Pacer) -> Groups:
    pacer.wait()
    body = json.dumps({"query": QUERY, "variables": {"slug": slug}}).encode()
    headers = {
        "Content-Type": "application/json",
        "Referer": STUDY_PLAN_PAGE,
        "User-Agent": "leetcode-for-robots list refresh",
    }
    payload = parse_json(read_url(url, body, headers), url)
    try:
        errors = payload.get("errors")
        if errors:
            raise ToolError(
                f"LeetCode rejected the query for {slug!r}: {errors[0]['message']}"
            )
        detail = payload["data"]["studyPlanV2Detail"]
        if detail is None:
            raise ToolError(f"LeetCode has no study plan {slug!r}")
        groups: Groups = []
        for group in detail["planSubGroups"]:
            problems = [
                (int(question["questionFrontendId"]), str(question["titleSlug"]))
                for question in group["questions"]
            ]
            if problems:
                groups.append((str(group["name"]), problems))
    except (KeyError, TypeError, ValueError, AttributeError, IndexError) as error:
        raise ToolError(
            f"the study plan {slug!r} came back in an unexpected shape ({error!r})"
        ) from error
    return groups


def fetch_rows(url: str) -> list[dict[str, Any]]:
    payload = parse_json(
        read_url(url, None, {"User-Agent": "leetcode-for-robots list refresh"}), url
    )
    if not isinstance(payload, list) or not all(isinstance(r, dict) for r in payload):
        raise ToolError(f"the site data at {url} is not a list of problem rows")
    return payload


def groups_from_rows(
    rows: list[dict[str, Any]], flag: str, ids_by_slug: dict[str, int]
) -> Groups:
    """Group the flagged rows by pattern. The slug names the problem; the catalog
    gives its id, because the number in a site data file name is not always the
    platform's id. A disagreement is reported, never silently kept."""
    chosen = [r for r in rows if flag == ALL_ROWS or r.get(flag)]
    if not chosen:
        raise ToolError(f"no rows in the site data are flagged {flag!r}")
    order: list[str] = []
    members: dict[str, list[tuple[int, str]]] = {}
    try:
        for r in chosen:
            pattern = str(r["pattern"])
            slug = str(r["link"]).strip("/")
            code = str(r["code"])
            if slug not in ids_by_slug:
                raise ToolError(
                    f"the site data names {slug!r} ({code}), "
                    "which is not in the catalog"
                )
            number = ids_by_slug[slug]
            if code.split("-")[0].isdigit() and int(code.split("-")[0]) != number:
                print(
                    f"warning: site data row {code!r} has number "
                    f"{int(code.split('-')[0])} but the catalog says {slug} is "
                    f"{number}; using the catalog",
                    file=sys.stderr,
                )
            if pattern not in members:
                order.append(pattern)
                members[pattern] = []
            members[pattern].append((number, slug))
    except KeyError as error:
        raise ToolError(f"a site data row is missing a field ({error!r})") from error
    return [(pattern, members[pattern]) for pattern in order]


def build_data(
    spec: ListSpec, groups: Groups, site: SiteData, retrieved_on: str
) -> dict[str, Any]:
    if spec.kind == PLAN_KIND:
        source: dict[str, str] = {
            "kind": PLAN_KIND,
            "url": f"{STUDY_PLAN_PAGE}{spec.reference}/",
            "plan_slug": spec.reference,
            "retrieved_on": retrieved_on,
            "note": NOTE,
        }
    else:
        source = {
            "kind": SITE_KIND,
            "url": site.page_url,
            "repository": site.repository,
            "revision": site.revision,
            "path": site.path,
            "license": site.license,
            "flag": spec.reference,
            "retrieved_on": retrieved_on,
            "note": NOTE,
        }
    return {
        "schema_version": 1,
        "id": spec.list_id,
        "name": spec.name,
        "platform": "leetcode",
        "size": spec.size,
        "source": source,
        "groups": [
            {
                "name": name,
                "problems": [{"id": number, "slug": slug} for number, slug in problems],
            }
            for name, problems in groups
        ],
    }


def render(data: dict[str, Any]) -> str:
    """One problem per line, so a changed list shows up as a small diff."""
    head = {k: v for k, v in data.items() if k != "groups"}
    lines = [json.dumps(head, indent=2)[:-2] + ",", '  "groups": [']
    blocks = []
    for group in data["groups"]:
        rows = ",\n".join(
            f"      {json.dumps(p, separators=(', ', ': '))}" for p in group["problems"]
        )
        blocks.append(
            f'    {{"name": {json.dumps(group["name"])}, "problems": [\n{rows}\n    ]}}'
        )
    lines.append(",\n".join(blocks))
    lines += ["  ]", "}", ""]
    return "\n".join(lines)


def load_registry(path: Path) -> tuple[SiteData, list[ListSpec]]:
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
        raise ToolError(f"cannot read the registry {path}: {error}") from error
    try:
        if (
            not isinstance(raw, dict)
            or set(raw) - REGISTRY_KEYS
            or raw.get("schema_version") != 1
        ):
            raise ValueError("unexpected top level or schema_version")
        site_raw = raw["site_data"]
        if set(site_raw) != SITE_KEYS or not re.fullmatch(
            r"[0-9a-f]{40}", site_raw["revision"]
        ):
            raise ValueError(
                "site_data needs repository, a 40 character revision, path and license"
            )
        site = SiteData(**site_raw)
        specs = []
        seen: set[str] = set()
        for item in raw["lists"]:
            if set(item) - LIST_KEYS:
                raise ValueError(f"unknown keys in {item.get('id')!r}")
            kind = item["kind"]
            if kind not in (PLAN_KIND, SITE_KIND):
                raise ValueError(f"unknown kind {kind!r}")
            reference = item["plan_slug"] if kind == PLAN_KIND else item["flag"]
            if not SLUG.fullmatch(item["id"]) or item["id"] in seen:
                raise ValueError(f"bad or repeated id {item['id']!r}")
            seen.add(item["id"])
            if isinstance(item["size"], bool) or not isinstance(item["size"], int):
                raise ValueError(f"size of {item['id']!r} must be a whole number")
            specs.append(
                ListSpec(
                    item["id"], str(item["name"]), kind, str(reference), item["size"]
                )
            )
    except (KeyError, TypeError, ValueError, AttributeError) as error:
        raise ToolError(f"the registry {path} is invalid: {error}") from error
    return site, specs


def write_registry(path: Path, site: SiteData, specs: list[ListSpec]) -> None:
    data = {
        "schema_version": 1,
        "site_data": {
            "repository": site.repository,
            "revision": site.revision,
            "path": site.path,
            "license": site.license,
        },
        "lists": [spec.to_dict() for spec in specs],
    }
    write_atomically(path, json.dumps(data, indent=2) + "\n")


def write_atomically(path: Path, text: str) -> None:
    handle, temporary = tempfile.mkstemp(
        dir=path.parent, prefix=".fetch-", suffix=".tmp"
    )
    try:
        with os.fdopen(handle, "w", encoding="utf-8", newline="\n") as stream:
            stream.write(text)
        os.replace(temporary, path)
    except BaseException:
        Path(temporary).unlink(missing_ok=True)
        raise


class Run:
    """One pass over some lists: fetch everything first, then judge, then write."""

    def __init__(
        self, args: argparse.Namespace, site: SiteData, catalog: Catalog
    ) -> None:
        self.args = args
        self.site = site
        self.catalog = catalog
        self.pacer = Pacer(args.delay)
        self.rows: list[dict[str, Any]] | None = None

    def groups_for(self, spec: ListSpec) -> Groups:
        if spec.kind == PLAN_KIND:
            return fetch_plan(self.args.leetcode_url, spec.reference, self.pacer)
        if self.rows is None:
            self.rows = fetch_rows(self.args.site_data_url or self.site.raw_url)
        ids = {e.slug: e.frontend_question_id for e in self.catalog.entries}
        return groups_from_rows(self.rows, spec.reference, ids)

    def build(self, spec: ListSpec) -> dict[str, Any]:
        data = build_data(
            spec, self.groups_for(spec), self.site, self.args.retrieved_on
        )
        try:
            parse_list(data, self.catalog)
        except ListError as error:
            raise ToolError(f"list {spec.list_id}: {error}") from error
        return data


def prepare(args: argparse.Namespace) -> tuple[SiteData, list[ListSpec], Run]:
    check_address(args.leetcode_url, "--leetcode-url")
    if args.site_data_url:
        check_address(args.site_data_url, "--site-data-url")
    try:
        catalog = load_catalog(args.catalog)
    except CatalogError as error:
        raise ToolError(str(error)) from error
    site, specs = load_registry(args.registry)
    return site, specs, Run(args, site, catalog)


def fetch_command(args: argparse.Namespace) -> int:
    site, specs, run = prepare(args)
    if args.only:
        unknown = sorted(set(args.only) - {s.list_id for s in specs})
        if unknown:
            raise UsageError(f"unknown list(s): {', '.join(unknown)}")
        specs = [s for s in specs if s.list_id in args.only]
    built = [(spec, run.build(spec)) for spec in specs]
    if args.check:
        return check_against_files(args.output_dir, built)
    args.output_dir.mkdir(parents=True, exist_ok=True)
    for spec, data in built:
        write_atomically(args.output_dir / f"{spec.list_id}.json", render(data))
        print(f"wrote {spec.list_id}: {data['size']} problems")
    return 0


def without_date(data: dict[str, Any]) -> dict[str, Any]:
    copy = json.loads(json.dumps(data))
    copy["source"].pop("retrieved_on", None)
    result: dict[str, Any] = copy
    return result


def check_against_files(
    directory: Path, built: list[tuple[ListSpec, dict[str, Any]]]
) -> int:
    different = []
    for spec, data in built:
        path = directory / f"{spec.list_id}.json"
        try:
            committed = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            different.append(
                f"{spec.list_id}: the committed file is missing or unreadable"
            )
            continue
        if without_date(committed) != without_date(data):
            different.append(
                f"{spec.list_id}: the committed file differs from its source"
            )
    for line in different:
        print(line, file=sys.stderr)
    if different:
        return 1
    print(f"{len(built)} list(s) match their sources")
    return 0


def plan_slug_from(value: str) -> str:
    if value.startswith(STUDY_PLAN_PAGE):
        value = value[len(STUDY_PLAN_PAGE) :].strip("/").split("/")[0]
    if not SLUG.fullmatch(value):
        raise UsageError(f"{value!r} is not a study plan slug or address")
    return value


def add_command(args: argparse.Namespace) -> int:
    site, specs, run = prepare(args)
    if not SLUG.fullmatch(args.id):
        raise UsageError("--id must be lowercase letters, digits and single hyphens")
    if any(spec.list_id == args.id for spec in specs):
        raise UsageError(f"the list id {args.id!r} is already registered")
    if args.leetcode_plan:
        kind, reference = PLAN_KIND, plan_slug_from(args.leetcode_plan)
    else:
        kind, reference = SITE_KIND, args.neetcode_flag
    provisional = ListSpec(args.id, args.name, kind, reference, args.size or 1)
    groups = run.groups_for(provisional)
    size = args.size or sum(len(problems) for _, problems in groups)
    spec = ListSpec(args.id, args.name, kind, reference, size)
    data = build_data(spec, groups, site, args.retrieved_on)
    try:
        parse_list(data, run.catalog)
    except ListError as error:
        raise ToolError(f"list {spec.list_id}: {error}") from error
    args.output_dir.mkdir(parents=True, exist_ok=True)
    write_atomically(args.output_dir / f"{spec.list_id}.json", render(data))
    write_registry(args.registry, site, [*specs, spec])
    print(f"added {spec.list_id}: {size} problems")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Refresh the curated problem lists.")
    parser.add_argument("--registry", type=Path, default=DEFAULT_REGISTRY)
    parser.add_argument("--catalog", type=Path, default=DEFAULT_CATALOG)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--leetcode-url", default=LEETCODE_URL)
    parser.add_argument("--site-data-url", default=None)
    parser.add_argument(
        "--delay", type=float, default=1.5, help="seconds between LeetCode requests"
    )
    parser.add_argument("--retrieved-on", default=date.today().isoformat())
    commands = parser.add_subparsers(dest="command", required=True)
    fetch = commands.add_parser("fetch", help="rebuild the registered lists")
    fetch.add_argument(
        "--check",
        action="store_true",
        help="compare with the committed files instead of writing",
    )
    fetch.add_argument("--only", nargs="+", metavar="ID")
    add = commands.add_parser("add", help="register a new list and fetch it")
    source = add.add_mutually_exclusive_group(required=True)
    source.add_argument(
        "--leetcode-plan",
        help="a study plan slug or its leetcode.com/studyplan address",
    )
    source.add_argument(
        "--neetcode-flag", help="a flag in the NeetCode site data, or * for every row"
    )
    add.add_argument("--id", required=True)
    add.add_argument("--name", required=True)
    add.add_argument(
        "--size",
        type=int,
        default=None,
        help="the published size (default: what was fetched)",
    )
    return parser


def main(argv: list[str]) -> int:
    args = build_parser().parse_args(argv)
    if args.delay < 0:
        print(
            "tools/fetch_lists.py: error: --delay must not be negative", file=sys.stderr
        )
        return 2
    try:
        date.fromisoformat(args.retrieved_on)
    except ValueError:
        print(
            "tools/fetch_lists.py: error: --retrieved-on must be an ISO date",
            file=sys.stderr,
        )
        return 2
    try:
        return fetch_command(args) if args.command == "fetch" else add_command(args)
    except UsageError as error:
        print(f"tools/fetch_lists.py: error: {error}", file=sys.stderr)
        return 2
    except ToolError as error:
        print(f"tools/fetch_lists.py: error: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
