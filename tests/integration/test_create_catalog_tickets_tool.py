# ABOUTME: Runs tools/create_catalog_tickets.py against a real local fake GitHub server.
# ABOUTME: Dry runs write nothing; reruns and crashes never create a duplicate ticket.

import json
import os
import shutil
import subprocess
import sys
import threading
import time
from collections.abc import Iterator
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, cast
from urllib.parse import parse_qs, urlsplit

import pytest

from practice.paths import REPO_ROOT

PLAN_TOOL = REPO_ROOT / "tools" / "plan_catalog.py"
TOOL = REPO_ROOT / "tools" / "create_catalog_tickets.py"
REPO = "owner/repo"
ROWS = [
    (1, "Two Sum", "two-sum", "easy", False, ["algorithms"], ["array"]),
    (2, "Problem 2", "problem-2", "easy", False, ["algorithms"], ["array"]),
    (3, "Problem 3", "problem-3", "medium", False, ["algorithms"], ["array"]),
    (4, "Problem 4", "problem-4", "easy", True, ["algorithms"], ["array"]),
    (5, "Problem 5", "problem-5", "hard", False, ["algorithms"], ["string"]),
]
RULES: dict[str, Any] = {
    "schema_version": 1,
    "ticket_size": 100,
    "individual": [{"problem": 1, "issue": 20}],
    "specialized": [
        {
            "id": "premium",
            "title": "premium problems",
            "reason": "Premium problems cannot be read without a subscription.",
            "match": {"premium": True},
        }
    ],
    "ignored_tags": [],
    "ignored_tags_note": "None.",
    "concepts": [
        {"id": "strings", "tags": ["string"]},
        {"id": "arrays", "tags": ["array"]},
    ],
    "fallback": {
        "id": "uncategorised",
        "title": "problems with no topic tags",
        "note": "LeetCode lists no topic tags for these problems.",
        "split_by_difficulty": False,
    },
}


class Fake(ThreadingHTTPServer):
    daemon_threads = True
    issues: list[dict[str, Any]]
    linked: list[int]
    seen: list[tuple[str, str, float, str]]
    fail_create_after: int | None
    created: int
    first_note_delay: float


class Handler(BaseHTTPRequestHandler):
    def _state(self) -> Fake:
        return cast(Fake, self.server)

    def _send(self, status: int, body: Any) -> None:
        raw = json.dumps(body).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)

    def _note(self) -> None:
        if not self._state().seen:
            time.sleep(self._state().first_note_delay)
        self._state().seen.append(
            (
                self.command,
                self.path,
                time.monotonic(),
                self.headers.get("Authorization", ""),
            )
        )

    def do_GET(self) -> None:
        state = self._state()
        self._note()
        parts = urlsplit(self.path)
        if parts.path == f"/repos/{REPO}/issues":
            query = parse_qs(parts.query)
            page = int(query["page"][0])
            size = int(query["per_page"][0])
            ordered = sorted(state.issues, key=lambda i: i["number"])
            self._send(200, ordered[(page - 1) * size : page * size])
        elif parts.path == f"/repos/{REPO}/issues/1/sub_issues":
            subs = [i for i in state.issues if i["number"] in state.linked]
            self._send(200, subs)
        elif parts.path.startswith(f"/repos/{REPO}/issues/"):
            number = int(parts.path.rsplit("/", 1)[1])
            found = [i for i in state.issues if i["number"] == number]
            self._send(200 if found else 404, found[0] if found else {})
        else:
            self._send(404, {})

    def do_POST(self) -> None:
        state = self._state()
        self._note()
        length = int(self.headers.get("Content-Length", "0"))
        body = json.loads(self.rfile.read(length))
        path = urlsplit(self.path).path
        if path == f"/repos/{REPO}/issues":
            if (
                state.fail_create_after is not None
                and state.created >= state.fail_create_after
            ):
                self._send(500, {})
                return
            state.created += 1
            number = 100 + len(state.issues)
            issue = {
                "number": number,
                "id": 9000 + number,
                "title": body["title"],
                "body": body["body"],
            }
            state.issues.append(issue)
            self._send(201, issue)
        elif path == f"/repos/{REPO}/issues/1/sub_issues":
            number = body["sub_issue_id"] - 9000
            state.linked.append(number)
            self._send(201, {"number": number})
        else:
            self._send(404, {})

    def log_message(self, format: str, *args: Any) -> None:
        return  # Keep test output pristine.


@pytest.fixture
def fake() -> Iterator[Fake]:
    httpd = Fake(("127.0.0.1", 0), Handler)
    httpd.issues = []
    httpd.linked = []
    httpd.seen = []
    httpd.fail_create_after = None
    httpd.created = 0
    httpd.first_note_delay = 0.0
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    yield httpd
    httpd.shutdown()
    httpd.server_close()
    thread.join()


class Work:
    def __init__(self, root: Path, fake: Fake) -> None:
        self.root = root
        self.fake = fake
        self.catalog = root / "leetcode.json"
        self.topics = root / "topics.json"
        self.rules = root / "rules.json"
        self.plan = root / "ticket-plan.json"
        self.curriculum = root / "core.json"
        shutil.copyfile(REPO_ROOT / "curriculum" / "core.json", self.curriculum)
        self.catalog.write_text(
            json.dumps(
                {
                    "platform": "leetcode",
                    "source_url": "https://leetcode.com/api/problems/all/",
                    "fetched_on": "2026-10-28",
                    "entries": [
                        {
                            "platform": "leetcode",
                            "frontend_question_id": n,
                            "question_id": n,
                            "title": t,
                            "slug": s,
                            "difficulty": d,
                            "paid_only": p,
                        }
                        for n, t, s, d, p, _, _ in ROWS
                    ],
                }
            ),
            encoding="utf-8",
        )
        self.topics.write_text(
            json.dumps(
                {
                    "schema_version": 1,
                    "platform": "leetcode",
                    "source_url": "https://leetcode.com/graphql",
                    "fetched_on": "2026-10-29",
                    "note": "Category and topic tag slugs only; no problem text.",
                    "entries": [
                        {"id": r[0], "categories": r[5], "topics": r[6]} for r in ROWS
                    ],
                }
            ),
            encoding="utf-8",
        )
        self.rules.write_text(json.dumps(RULES), encoding="utf-8")
        shared = [
            "--catalog",
            str(self.catalog),
            "--topics",
            str(self.topics),
            "--rules",
            str(self.rules),
            "--curriculum",
            str(self.curriculum),
            "--plan",
            str(self.plan),
        ]
        planned = subprocess.run(
            [
                sys.executable,
                "-I",
                str(PLAN_TOOL),
                *shared,
                "--lists-dir",
                str(root / "lists"),
                "--problems-dir",
                str(root / "problems"),
                "plan",
            ],
            capture_output=True,
            text=True,
            check=False,
            timeout=120,
        )
        assert planned.returncode == 0, planned.stderr
        self.shared = shared

    def run(
        self, *extra: str, token: str | None = "secret", delay: str = "0"
    ) -> subprocess.CompletedProcess[str]:
        port = self.fake.server_address[1]
        env = {k: v for k, v in os.environ.items() if k != "GITHUB_TOKEN"}
        if token is not None:
            env["GITHUB_TOKEN"] = token
        return subprocess.run(
            [
                sys.executable,
                "-I",
                str(TOOL),
                *self.shared,
                "--repo",
                REPO,
                "--api-url",
                f"http://127.0.0.1:{port}",
                "--delay",
                delay,
                *extra,
            ],
            capture_output=True,
            text=True,
            check=False,
            timeout=120,
            env=env,
        )

    def classes(self) -> list[dict[str, Any]]:
        loaded = json.loads(self.plan.read_text(encoding="utf-8"))
        found: list[dict[str, Any]] = loaded["classes"]
        return found

    def to_create(self) -> list[dict[str, Any]]:
        return [c for c in self.classes() if c["kind"] == "class"]


@pytest.fixture
def work(tmp_path: Path, fake: Fake) -> Work:
    return Work(tmp_path, fake)


def posts(fake: Fake) -> list[str]:
    return [path for method, path, _, _ in fake.seen if method == "POST"]


def test_a_dry_run_changes_nothing_anywhere(work: Work, fake: Fake) -> None:
    before = work.plan.read_text(encoding="utf-8")
    result = work.run()
    assert result.returncode == 0, result.stderr
    assert posts(fake) == []
    assert fake.issues == []
    assert work.plan.read_text(encoding="utf-8") == before
    count = len(work.to_create())
    assert f"would create {count}" in result.stdout
    assert "dry run, nothing written" in result.stdout


def test_apply_creates_one_issue_per_class_and_records_the_numbers(
    work: Work, fake: Fake
) -> None:
    result = work.run("--apply")
    assert result.returncode == 0, result.stderr
    classes = work.to_create()
    assert len(fake.issues) == len(classes)
    assert all(c["issue"] is not None for c in classes)
    assert {c["issue"] for c in classes} == {i["number"] for i in fake.issues}
    assert {c["title"] for c in classes} == {i["title"] for i in fake.issues}
    assert sorted(fake.linked) == sorted(i["number"] for i in fake.issues)


def test_the_starter_ticket_is_left_alone(work: Work, fake: Fake) -> None:
    assert work.run("--apply").returncode == 0
    starter = next(c for c in work.classes() if c["kind"] == "individual")
    assert starter["issue"] == 20
    assert 20 not in fake.linked


def test_a_created_issue_carries_the_ticket_body_without_its_title_line(
    work: Work, fake: Fake
) -> None:
    assert work.run("--apply").returncode == 0
    issue = fake.issues[0]
    assert not issue["body"].startswith("# ")
    assert "Sub-issue of #1" in issue["body"]
    assert "Readiness" in issue["body"] or "ready when" in issue["body"]


def test_a_second_apply_creates_and_links_nothing(work: Work, fake: Fake) -> None:
    assert work.run("--apply").returncode == 0
    before = (len(fake.issues), len(fake.linked), len(posts(fake)))
    result = work.run("--apply")
    assert result.returncode == 0, result.stderr
    assert (len(fake.issues), len(fake.linked), len(posts(fake))) == before
    assert "create 0" in result.stdout and "link 0" in result.stdout


def test_an_existing_issue_with_the_exact_title_is_adopted_not_duplicated(
    work: Work, fake: Fake
) -> None:
    title = work.to_create()[0]["title"]
    fake.issues.append({"number": 77, "id": 9077, "title": title, "body": ""})
    assert work.run("--apply").returncode == 0
    assert [i["title"] for i in fake.issues].count(title) == 1
    assert work.to_create()[0]["issue"] == 77
    assert 77 in fake.linked


def test_a_title_that_only_contains_the_planned_one_is_not_adopted(
    work: Work, fake: Fake
) -> None:
    title = work.to_create()[0]["title"]
    fake.issues.append(
        {"number": 77, "id": 9077, "title": f"{title} (extra)", "body": ""}
    )
    assert work.run("--apply").returncode == 0
    assert work.to_create()[0]["issue"] != 77
    assert 77 not in fake.linked


def test_a_pull_request_with_the_planned_title_is_not_adopted(
    work: Work, fake: Fake
) -> None:
    title = work.to_create()[0]["title"]
    fake.issues.append(
        {"number": 77, "id": 9077, "title": title, "body": "", "pull_request": {}}
    )
    assert work.run("--apply").returncode == 0
    assert work.to_create()[0]["issue"] != 77
    assert 77 not in fake.linked


def test_a_matching_issue_beyond_the_first_page_is_still_adopted(
    work: Work, fake: Fake
) -> None:
    for number in range(200, 305):
        fake.issues.append(
            {"number": number, "id": 9000 + number, "title": f"other {number}"}
        )
    title = work.to_create()[0]["title"]
    fake.issues.append({"number": 400, "id": 9400, "title": title, "body": ""})
    assert work.run("--apply").returncode == 0
    assert [i["title"] for i in fake.issues].count(title) == 1
    assert work.to_create()[0]["issue"] == 400


def test_two_issues_with_the_planned_title_stop_the_run(work: Work, fake: Fake) -> None:
    title = work.to_create()[0]["title"]
    for number in (77, 78):
        fake.issues.append(
            {"number": number, "id": 9000 + number, "title": title, "body": ""}
        )
    result = work.run("--apply")
    assert result.returncode == 1
    assert "#77" in result.stderr and "#78" in result.stderr
    assert posts(fake) == []


def test_a_crash_midway_keeps_what_was_done_and_a_rerun_finishes_without_duplicates(
    work: Work, fake: Fake
) -> None:
    fake.fail_create_after = 1
    result = work.run("--apply")
    assert result.returncode == 1
    assert len(fake.issues) == 1
    numbered = [c for c in work.to_create() if c["issue"] is not None]
    assert [c["issue"] for c in numbered] == [fake.issues[0]["number"]]
    fake.fail_create_after = None
    assert work.run("--apply").returncode == 0
    titles = [i["title"] for i in fake.issues]
    assert len(titles) == len(set(titles)) == len(work.to_create())
    assert sorted(fake.linked) == sorted(i["number"] for i in fake.issues)


def test_a_ticket_created_but_not_yet_linked_is_linked_on_the_next_run(
    work: Work, fake: Fake
) -> None:
    assert work.run("--apply").returncode == 0
    dropped = fake.linked.pop()
    assert work.run("--apply").returncode == 0
    assert dropped in fake.linked
    assert len(fake.linked) == len(set(fake.linked))


@pytest.mark.parametrize("first_note_delay", [0.0, 0.1])
def test_requests_are_spaced_by_the_delay(
    work: Work, fake: Fake, first_note_delay: float
) -> None:
    fake.first_note_delay = first_note_delay
    assert work.run("--apply", delay="0.15").returncode == 0
    times = [t for _, _, t, _ in fake.seen]
    gaps = [b - a for a, b in zip(times, times[1:], strict=False)]
    assert gaps and min(gaps) >= 0.14


def test_the_token_is_sent_only_as_an_authorization_header(
    work: Work, fake: Fake
) -> None:
    result = work.run("--apply", token="tok-123")
    assert result.returncode == 0
    assert all(auth == "Bearer tok-123" for _, _, _, auth in fake.seen)
    assert "tok-123" not in result.stdout + result.stderr
    assert "tok-123" not in work.plan.read_text(encoding="utf-8")


def test_apply_without_a_token_is_a_usage_error_and_sends_nothing(
    work: Work, fake: Fake
) -> None:
    result = work.run("--apply", token=None)
    assert result.returncode == 2
    assert "GITHUB_TOKEN" in result.stderr
    assert fake.seen == []


def test_a_plain_http_remote_address_is_refused(work: Work, fake: Fake) -> None:
    command = [
        sys.executable,
        "-I",
        str(TOOL),
        *work.shared,
        "--api-url",
        "http://example.com",
    ]
    result = subprocess.run(
        command, capture_output=True, text=True, check=False, timeout=60
    )
    assert result.returncode == 2
    assert "https" in result.stderr


def test_a_repository_the_server_does_not_know_fails_cleanly_and_writes_nothing(
    work: Work, fake: Fake
) -> None:
    before = work.plan.read_text(encoding="utf-8")
    result = work.run("--apply", "--repo", "owner/other")
    assert result.returncode == 1
    assert "HTTP 404" in result.stderr
    assert "Traceback" not in result.stderr
    assert fake.issues == []
    assert work.plan.read_text(encoding="utf-8") == before
