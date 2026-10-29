# ABOUTME: Runs tools/fetch_catalog_topics.py against a real local HTTP server.
# ABOUTME: A failed or inconsistent fetch must write nothing, and paging must be honest.

import json
import subprocess
import sys
import threading
import time
from collections.abc import Iterator
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, cast

import pytest

from practice.paths import REPO_ROOT

TOOL = REPO_ROOT / "tools" / "fetch_catalog_topics.py"
CATALOG = {
    "platform": "leetcode",
    "source_url": "https://leetcode.com/api/problems/all/",
    "fetched_on": "2026-10-28",
    "entries": [
        {
            "platform": "leetcode",
            "frontend_question_id": n,
            "question_id": n,
            "title": f"Problem {n}",
            "slug": f"problem-{n}",
            "difficulty": "easy",
            "paid_only": n == 5,
        }
        for n in range(1, 8)
    ],
}
TAGS = {
    1: ["hash-table", "array"],
    2: ["linked-list"],
    3: [],
    4: ["database"],
    5: ["string"],
    6: ["interactive", "binary-search"],
    7: ["array"],
}
CATEGORIES = {
    "algorithms": [1, 2, 3, 5, 6],
    "database": [4],
    "pandas": [4, 7],
    "javascript": [],
    "shell": [],
    "concurrency": [],
}


def question(n: int) -> dict[str, Any]:
    return {
        "frontendQuestionId": str(n),
        "titleSlug": f"problem-{n}",
        "isPaidOnly": n == 5,
        "difficulty": "Easy",
        "topicTags": [{"slug": t, "name": t.title()} for t in TAGS[n]],
    }


class Server(ThreadingHTTPServer):
    daemon_threads = True
    categories: dict[str, list[int]]
    everything: list[int]
    mutate: Any
    status: int
    redirect: bool
    garbage: bool
    total_lie: bool
    requests: list[tuple[str, int, int]]
    times: list[float]


class Handler(BaseHTTPRequestHandler):
    def do_POST(self) -> None:
        server = cast(Server, self.server)
        length = int(self.headers.get("Content-Length", "0"))
        request = json.loads(self.rfile.read(length))
        server.times.append(time.monotonic())
        variables = request["variables"]
        slug = variables["categorySlug"]
        skip, limit = variables["skip"], variables["limit"]
        server.requests.append((slug, skip, limit))
        if server.redirect:
            self.send_response(302)
            self.send_header("Location", "http://127.0.0.1:9/x")
            self.send_header("Content-Length", "0")
            self.end_headers()
            return
        if server.status != 200:
            self._send(server.status, b"{}")
            return
        if server.garbage:
            self._send(200, b"<html>no</html>")
            return
        ids = server.everything if slug == "" else server.categories[slug]
        page = ids[skip : skip + limit]
        questions = [server.mutate(question(n)) for n in page]
        total = len(ids) + (5 if server.total_lie else 0)
        body = {
            "data": {"problemsetQuestionList": {"total": total, "questions": questions}}
        }
        self._send(200, json.dumps(body).encode())

    def _send(self, status: int, body: bytes) -> None:
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format: str, *args: Any) -> None:
        return  # Keep test output pristine.


@pytest.fixture
def server() -> Iterator[Server]:
    httpd = Server(("127.0.0.1", 0), Handler)
    httpd.categories = {k: list(v) for k, v in CATEGORIES.items()}
    httpd.everything = list(range(1, 8))
    httpd.mutate = lambda q: q
    httpd.status = 200
    httpd.redirect = httpd.garbage = httpd.total_lie = False
    httpd.requests = []
    httpd.times = []
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    yield httpd
    httpd.shutdown()
    httpd.server_close()
    thread.join()


class Work:
    def __init__(self, root: Path, server: Server) -> None:
        self.server = server
        self.catalog = root / "leetcode.json"
        self.output = root / "topics.json"
        self.catalog.write_text(json.dumps(CATALOG), encoding="utf-8")

    def run(self, *extra: str, delay: str = "0") -> subprocess.CompletedProcess[str]:
        port = self.server.server_address[1]
        command = [
            sys.executable,
            "-I",
            str(TOOL),
            "--catalog",
            str(self.catalog),
            "--output",
            str(self.output),
            "--leetcode-url",
            f"http://127.0.0.1:{port}/graphql",
            "--delay",
            delay,
            "--fetched-on",
            "2026-10-29",
            *extra,
        ]
        return subprocess.run(
            command, capture_output=True, text=True, check=False, timeout=90
        )

    def data(self) -> dict[str, Any]:
        loaded = json.loads(self.output.read_text(encoding="utf-8"))
        assert isinstance(loaded, dict)
        return loaded


@pytest.fixture
def work(tmp_path: Path, server: Server) -> Work:
    return Work(tmp_path, server)


def test_the_file_has_one_entry_per_problem_with_sorted_categories_and_topics(
    work: Work,
) -> None:
    result = work.run()
    assert result.returncode == 0, result.stderr
    entries = {e["id"]: e for e in work.data()["entries"]}
    assert sorted(entries) == list(range(1, 8))
    assert entries[1] == {
        "id": 1,
        "categories": ["algorithms"],
        "topics": ["array", "hash-table"],
    }
    assert entries[4]["categories"] == ["database", "pandas"]  # In two categories.
    assert entries[7]["categories"] == ["pandas"]
    assert entries[3]["topics"] == []
    assert entries[6]["topics"] == ["binary-search", "interactive"]


def test_the_file_records_provenance_and_stores_no_problem_text(work: Work) -> None:
    assert work.run().returncode == 0
    data = work.data()
    assert data["source_url"] == "https://leetcode.com/graphql"
    assert data["fetched_on"] == "2026-10-29"
    assert "no problem text" in data["note"]
    text = json.dumps(data)
    assert "Problem 1" not in text and "problem-1" not in text


def test_running_again_gives_a_byte_identical_file(work: Work) -> None:
    assert work.run().returncode == 0
    first = work.output.read_bytes()
    assert work.run().returncode == 0
    assert work.output.read_bytes() == first


def test_paging_asks_for_every_page_of_every_category(
    work: Work, server: Server
) -> None:
    assert work.run("--page-size", "3").returncode == 0
    everything = [(skip, limit) for slug, skip, limit in server.requests if slug == ""]
    assert everything == [(0, 3), (3, 3), (6, 3)]
    asked = {slug for slug, _, _ in server.requests}
    assert asked == {"", *CATEGORIES}


def test_requests_are_spaced_by_the_delay(work: Work, server: Server) -> None:
    result = work.run("--page-size", "7", delay="0.2")
    assert result.returncode == 0, result.stderr
    gaps = [b - a for a, b in zip(server.times, server.times[1:], strict=False)]
    assert gaps and min(gaps) >= 0.15


def test_check_passes_on_an_unchanged_source_and_ignores_the_date(work: Work) -> None:
    assert work.run().returncode == 0
    data = work.data()
    data["fetched_on"] = "2020-01-01"
    work.output.write_text(json.dumps(data), encoding="utf-8")
    result = work.run("--check")
    assert result.returncode == 0, result.stderr
    assert "match" in result.stdout.lower()


def test_check_fails_when_a_topic_changed(work: Work, server: Server) -> None:
    assert work.run().returncode == 0
    TAGS[7] = ["array", "math"]
    try:
        result = work.run("--check")
    finally:
        TAGS[7] = ["array"]
    assert result.returncode == 1
    assert "differs" in result.stderr


@pytest.mark.parametrize(
    ("setting", "message"),
    [("status", "429"), ("redirect", "redirect"), ("garbage", "not valid JSON")],
)
def test_a_bad_response_fails_clearly_and_writes_nothing(
    work: Work, server: Server, setting: str, message: str
) -> None:
    if setting == "status":
        server.status = 429
    else:
        setattr(server, setting, True)
    result = work.run()
    assert result.returncode == 1
    assert message in result.stderr
    assert not work.output.exists()


def test_a_missing_problem_fails_and_writes_nothing(work: Work, server: Server) -> None:
    server.everything.remove(3)
    result = work.run()
    assert result.returncode == 1
    assert "problem 3" in result.stderr
    assert not work.output.exists()


def test_a_slug_that_disagrees_with_the_catalog_fails(
    work: Work, server: Server
) -> None:
    def rename(q: dict[str, Any]) -> dict[str, Any]:
        if q["frontendQuestionId"] == "2":
            q["titleSlug"] = "something-else"
        return q

    server.mutate = rename
    result = work.run()
    assert result.returncode == 1
    assert "problem 2" in result.stderr and "something-else" in result.stderr
    assert not work.output.exists()


def test_a_premium_flag_that_disagrees_with_the_catalog_fails(
    work: Work, server: Server
) -> None:
    def flip(q: dict[str, Any]) -> dict[str, Any]:
        if q["frontendQuestionId"] == "5":
            q["isPaidOnly"] = False
        return q

    server.mutate = flip
    result = work.run()
    assert result.returncode == 1
    assert "problem 5" in result.stderr and "premium" in result.stderr
    assert not work.output.exists()


def test_a_problem_in_no_category_fails(work: Work, server: Server) -> None:
    server.categories["algorithms"].remove(6)
    result = work.run()
    assert result.returncode == 1
    assert "problem 6" in result.stderr and "category" in result.stderr
    assert not work.output.exists()


def test_a_total_that_promises_more_than_it_delivers_fails(
    work: Work, server: Server
) -> None:
    server.total_lie = True
    result = work.run("--page-size", "3")
    assert result.returncode == 1
    assert "total" in result.stderr
    assert not work.output.exists()


def test_a_remote_http_address_is_refused_before_any_request(
    work: Work, server: Server
) -> None:
    command = [
        sys.executable,
        "-I",
        str(TOOL),
        "--catalog",
        str(work.catalog),
        "--output",
        str(work.output),
        "--leetcode-url",
        "http://example.test/graphql",
    ]
    result = subprocess.run(command, capture_output=True, text=True, timeout=60)
    assert result.returncode == 2
    assert "https" in result.stderr
    assert server.requests == []
