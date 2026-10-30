# ABOUTME: Fetches source-attributed Python3 signatures, constraints and examples.
# ABOUTME: Keeps sourced text in ignored scratch storage for readiness verification.

import argparse
import ast
import hashlib
import json
import math
import os
import re
import subprocess
import sys
import tempfile
import time
from datetime import UTC, datetime
from html.parser import HTMLParser
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

from practice.paths import REPO_ROOT
from practice.source_fetch import FetchError, address_refusal, fetch_url

LEETCODE_URL = "https://leetcode.com/graphql"
QUERY = (
    "query problemFacts($titleSlug: String!) { question(titleSlug: $titleSlug) { "
    "questionId questionFrontendId titleSlug title isPaidOnly content "
    "codeSnippets { langSlug code } } }"
)
SLUG = re.compile(r"[a-z0-9]+(?:-[a-z0-9]+)*")
DEFAULT_OUTPUT = REPO_ROOT / ".scratch" / "problem-facts"


class ToolError(Exception):
    """Source facts are unavailable, ambiguous or unsafe to save."""


class FactsHTML(HTMLParser):
    """Render text while marking actual lists and retaining math semantics."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.parts: list[str] = []
        self.stack: list[str] = []
        self.math_starts: list[int] = []
        self.example_depths: list[int] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag in {"img", "svg", "math", "script", "style", "table"}:
            raise ToolError(f"unsupported problem HTML element <{tag}>")
        if tag in {"p", "div", "pre", "br", "h1", "h2", "h3", "h4"}:
            self.parts.append("\n")
        classes = dict(attrs).get("class") or ""
        if tag == "pre" or (tag == "div" and "example-block" in classes.split()):
            self.parts.append("\x02")
            self.example_depths.append(len(self.stack))
        if tag in {"ul", "ol"}:
            self.parts.append("\n\x1d")
        if tag == "li":
            self.parts.append("\n\x1e")
        if tag == "sup":
            self.parts.append("^")
        if tag == "sub":
            self.parts.append("_")
        if tag in {"sup", "sub"}:
            self.math_starts.append(len(self.parts))
        if tag not in {"br", "hr", "wbr"}:
            self.stack.append(tag)

    def handle_startendtag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        self.handle_starttag(tag, attrs)
        if tag not in {"br", "hr", "wbr"}:
            self.handle_endtag(tag)

    def handle_endtag(self, tag: str) -> None:
        if not self.stack or self.stack[-1] != tag:
            raise ToolError("malformed problem HTML: unbalanced tags")
        self.stack.pop()
        if self.example_depths and self.example_depths[-1] == len(self.stack):
            self.example_depths.pop()
            self.parts.append("\x03")
        if tag in {"sup", "sub"}:
            start = self.math_starts.pop()
            expression = "".join(self.parts[start:]).strip()
            if not expression:
                raise ToolError("empty superscript or subscript")
            if not re.fullmatch(r"-?[0-9]+|[a-zA-Z]", expression):
                self.parts[start:] = [f"({expression})"]
        if tag in {"p", "div", "pre", "li", "h1", "h2", "h3", "h4"}:
            self.parts.append("\n")
        if tag in {"ul", "ol"}:
            self.parts.append("\x1f\n")

    def handle_data(self, data: str) -> None:
        if any(char in data for char in "\x02\x03\x1d\x1e\x1f"):
            raise ToolError("unsupported control character in problem HTML")
        self.parts.append(data)


def clean(text: str) -> str:
    return "\n".join(
        line for row in text.replace("\xa0", " ").splitlines() if (line := row.strip())
    )


def content_facts(html: str) -> tuple[list[str], list[dict[str, Any]]]:
    parser = FactsHTML()
    try:
        parser.feed(html)
        parser.close()
    except (ValueError, RecursionError) as error:
        raise ToolError("malformed problem HTML") from error
    if parser.stack:
        raise ToolError("malformed problem HTML: unclosed tags")
    text = "".join(parser.parts)
    headings = list(re.finditer(r"(?im)^[ \t\r\n]*Constraints[ \t]*:[ \t\r\n]*", text))
    if len(headings) != 1:
        raise ToolError("missing or ambiguous Constraints heading")
    heading = headings[0]
    tail = text[heading.end() :].lstrip(" \t\r\n")
    if not tail.startswith("\x1d") or "\x1f" not in tail:
        raise ToolError("unsupported constraints: expected a labeled list")
    listed = tail[1 : tail.index("\x1f")]
    if "\x1d" in listed or not listed.lstrip(" \t\r\n").startswith("\x1e"):
        raise ToolError("unsupported nested or malformed constraints list")
    constraints = [clean(item) for item in listed.split("\x1e")[1:]]
    if not constraints or not all(constraints):
        raise ToolError("missing constraint items")
    before = text[: heading.start()]
    markers = list(re.finditer(r"(?im)^\s*Example\s+(\d+)\s*:\s*", before))
    if not markers or len(re.findall(r"(?i)\bExample\s+\d+\s*:", text)) != len(markers):
        raise ToolError("missing or unsupported numbered examples")
    examples: list[dict[str, Any]] = []
    for index, marker in enumerate(markers):
        if int(marker[1]) != index + 1:
            raise ToolError("examples must be numbered consecutively from 1")
        end = markers[index + 1].start() if index + 1 < len(markers) else len(before)
        section = before[marker.end() : end]
        section = re.split(r"(?im)^\s*(?:Follow[- ]?up|Hints?)\s*:", section)[0]
        if section.count("\x02") != 1 or section.count("\x03") != 1:
            raise ToolError(f"example {index + 1}: unsupported example container")
        prefix, remainder = section.split("\x02")
        section, suffix = remainder.split("\x03")
        if clean(prefix) or clean(suffix):
            raise ToolError(f"example {index + 1}: content outside example container")
        section = section.replace("\x1d", "").replace("\x1e", "").replace("\x1f", "")
        labels = list(re.finditer(r"\b(Input|Output|Explanation)\s*:\s*", section))
        names = [match[1] for match in labels]
        if names not in (["Input", "Output"], ["Input", "Output", "Explanation"]):
            raise ToolError(
                f"example {index + 1}: missing or ambiguous Input/Output labels"
            )
        item: dict[str, Any] = {"number": index + 1}
        if clean(section[: labels[0].start()]):
            raise ToolError(f"example {index + 1}: unsupported content before Input")
        for position, label in enumerate(labels):
            stop = (
                labels[position + 1].start()
                if position + 1 < len(labels)
                else len(section)
            )
            value = clean(section[label.end() : stop])
            if not value:
                raise ToolError(f"example {index + 1}: empty {label[1]}")
            item[label[1].lower()] = value
        examples.append(item)
    return constraints, examples


def signature(snippets: Any) -> str:
    if not isinstance(snippets, list) or not all(isinstance(s, dict) for s in snippets):
        raise ToolError("malformed Python3 codeSnippets")
    python = [s for s in snippets if s.get("langSlug") == "python3"]
    if len(python) != 1 or not isinstance(python[0].get("code"), str):
        raise ToolError("expected exactly one Python3 snippet")
    code = python[0]["code"]
    # The platform leaves the final method suite blank. Only this exact empty
    # suite gets an inert AST placeholder; no snippet is ever executed or saved.
    empty = re.search(r"(?m)^( +)def [^\n]+:[ \t]*\n[ \t\r\n]*\Z", code)
    if empty:
        code = code.rstrip() + "\n" + empty[1] + "    pass\n"
    try:
        tree = ast.parse(code)
    except (SyntaxError, ValueError, RecursionError) as error:
        raise ToolError("malformed Python3 snippet") from error
    classes = [node for node in tree.body if isinstance(node, ast.ClassDef)]
    if len(classes) != 1 or classes[0].name != "Solution":
        raise ToolError("unsupported Python3 shape: expected one Solution class")
    cls = classes[0]
    methods = [
        n for n in cls.body if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))
    ]
    if len(methods) != 1 or not isinstance(methods[0], ast.FunctionDef):
        raise ToolError(
            "unsupported Python3 shape: expected one Solution method; "
            "stateful APIs need manual verification"
        )
    method = methods[0]
    args = method.args
    if (
        cls.bases
        or cls.decorator_list
        or method.decorator_list
        or method.name.startswith("_")
        or not args.args
        or args.args[0].arg != "self"
        or args.posonlyargs
        or args.vararg
        or args.kwarg
        or args.kwonlyargs
        or args.defaults
        or method.type_params
        or method.returns is None
        or any(a.annotation is None for a in args.args[1:])
    ):
        raise ToolError("unsupported Python3 method signature")
    return f"def {method.name}({ast.unparse(args)}) -> {ast.unparse(method.returns)}:"


def parse_facts(raw: bytes, slug: str, endpoint: str) -> dict[str, Any]:
    try:
        payload = json.loads(raw)
    except (json.JSONDecodeError, UnicodeDecodeError, RecursionError) as error:
        raise ToolError("response is not valid JSON") from error
    if not isinstance(payload, dict) or payload.get("errors"):
        raise ToolError("GraphQL query failed or returned an unsupported response")
    data = payload.get("data")
    if not isinstance(data, dict) or "question" not in data:
        raise ToolError("malformed GraphQL question response")
    question = data["question"]
    if question is None:
        raise ToolError(f"unknown problem slug {slug!r}")
    if not isinstance(question, dict):
        raise ToolError("malformed question record")
    if type(question.get("isPaidOnly")) is not bool:
        raise ToolError("missing or malformed isPaidOnly flag")
    if question["isPaidOnly"]:
        raise ToolError(f"{slug}: premium problem; facts are unavailable")
    for field in ("questionId", "questionFrontendId", "titleSlug", "title", "content"):
        if not isinstance(question.get(field), str) or not question[field].strip():
            raise ToolError(f"missing or malformed question {field}")
    if question["titleSlug"] != slug:
        raise ToolError("returned slug does not match requested slug")
    method = signature(question.get("codeSnippets"))
    constraints, examples = content_facts(question["content"])
    return {
        "schema_version": 1,
        "platform": "leetcode",
        "requested_slug": slug,
        "slug": question["titleSlug"],
        "title": question["title"],
        "question_id": question["questionId"],
        "frontend_question_id": question["questionFrontendId"],
        "python3_signature": method,
        "constraints": constraints,
        "examples": examples,
        "source": {
            "graphql_url": endpoint,
            "problem_url": f"https://leetcode.com/problems/{slug}/",
            "fetched_at": datetime.now(UTC).isoformat(),
            "response_sha256": hashlib.sha256(raw).hexdigest(),
        },
        "purpose": (
            "Readiness verification input; "
            "not platform acceptance or hidden-test evidence."
        ),
    }


def git_probe(
    directory: Path, arguments: list[str]
) -> subprocess.CompletedProcess[str]:
    try:
        return subprocess.run(
            ["git", "-C", str(directory), *arguments],
            capture_output=True,
            text=True,
            check=False,
            timeout=10,
        )
    except (subprocess.TimeoutExpired, OSError) as error:
        raise ToolError("Git output-safety verification could not finish") from error


def output_directory(path: Path, names: list[str]) -> Path:
    lexical = Path(os.path.abspath(path))
    root = REPO_ROOT.resolve()
    scratch = root / ".scratch"
    resolved = lexical.resolve()
    if lexical.is_relative_to(root):
        if not lexical.is_relative_to(scratch) or not resolved.is_relative_to(scratch):
            raise ToolError(
                "output inside this repository must stay under its "
                "ignored .scratch directory"
            )
    elif resolved.is_relative_to(root):
        raise ToolError("external output resolves inside this repository")
    # Git, rather than a directory-name guess, decides whether a destination in
    # another checkout is ignored. Check a prospective output file as well.
    ancestor = resolved
    while not ancestor.exists():
        ancestor = ancestor.parent
    result = git_probe(ancestor, ["rev-parse", "--show-toplevel"])
    markers = [directory / ".git" for directory in (ancestor, *ancestor.parents)]
    if result.returncode != 0:
        if (
            any(marker.exists() or marker.is_symlink() for marker in markers)
            or "not a git repository" not in result.stderr.lower()
        ):
            raise ToolError(
                "Git checkout status could not be verified; refusing output"
            )
    if result.returncode == 0:
        for name in [*names, ".problem-facts-stage-check.tmp"]:
            ignored = git_probe(ancestor, ["check-ignore", str(resolved / name)])
            if ignored.returncode != 0:
                kind = (
                    "staging path" if name.startswith(".problem-facts-") else "output"
                )
                raise ToolError(
                    f"{kind} in a Git checkout must be ignored; "
                    "use .scratch or an external directory"
                )
    return resolved


def write_fact(path: Path, facts: dict[str, Any]) -> None:
    if path.is_symlink():
        raise ToolError(f"refusing symlink output file {path}")
    handle, stage = tempfile.mkstemp(
        dir=path.parent, prefix=".problem-facts-", suffix=".tmp"
    )
    try:
        with os.fdopen(handle, "w", encoding="utf-8", newline="\n") as stream:
            output_directory(path.parent, [path.name, Path(stage).name])
            stream.write(json.dumps(facts, indent=2, ensure_ascii=False) + "\n")
        # Linking publishes complete bytes atomically and refuses an existing
        # destination, including one created by another process during fetching.
        os.link(stage, path)
    finally:
        Path(stage).unlink(missing_ok=True)


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(
        description="Fetch readiness verification facts into ignored scratch storage."
    )
    parser.add_argument("slugs", nargs="+")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--leetcode-url", default=LEETCODE_URL)
    parser.add_argument(
        "--delay",
        type=float,
        default=1.0,
        help="minimum seconds between requests (positive, default: 1)",
    )
    args = parser.parse_args(argv)
    if not math.isfinite(args.delay) or args.delay <= 0:
        parser.error("--delay must be finite and positive")
    if any(not SLUG.fullmatch(slug) for slug in args.slugs):
        parser.error(
            "slugs must contain only lowercase letters, digits and separating hyphens"
        )
    try:
        parts = urlsplit(args.leetcode_url)
        if (
            not parts.hostname
            or parts.username
            or parts.password
            or parts.query
            or parts.fragment
        ):
            parser.error(
                "endpoint must have a hostname and no credentials, query or fragment"
            )
        refusal = address_refusal(args.leetcode_url)
    except ValueError:
        parser.error("malformed endpoint URL")
    if refusal:
        parser.error(refusal)
    try:
        slugs = list(dict.fromkeys(args.slugs))
        names = [slug + ".json" for slug in slugs]
        destination = output_directory(args.output, names)
        facts: list[dict[str, Any]] = []
        last: float | None = None
        for slug in slugs:
            if last is not None:
                time.sleep(max(0, args.delay - (time.monotonic() - last)))
            raw = fetch_url(
                args.leetcode_url,
                data=json.dumps(
                    {"query": QUERY, "variables": {"titleSlug": slug}}
                ).encode(),
                headers={
                    "Content-Type": "application/json",
                    "Referer": f"https://leetcode.com/problems/{slug}/",
                },
            )
            last = time.monotonic()
            facts.append(parse_facts(raw, slug, args.leetcode_url))
        # Validate every target before publishing any source text. Publication is
        # atomic per file; a filesystem failure can still leave a published prefix.
        for slug in slugs:
            target = destination / f"{slug}.json"
            if target.is_symlink() or target.exists():
                raise ToolError(
                    f"refusing existing output target {target}; "
                    "choose a fresh directory"
                )
        destination.mkdir(parents=True, exist_ok=True)
        if output_directory(args.output, names) != destination:
            raise ToolError("output destination changed while fetching")
        for slug, fact in zip(slugs, facts, strict=True):
            write_fact(destination / f"{slug}.json", fact)
            print(f"wrote {destination / (slug + '.json')}")
    except (ToolError, FetchError, OSError, ValueError, OverflowError) as error:
        print(f"problem facts: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
