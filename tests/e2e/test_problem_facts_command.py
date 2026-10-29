# ABOUTME: Exercises the facts command using real HTTP and Python subprocesses.
# ABOUTME: Invented source records check request pacing, failures and safe storage.

import hashlib
import json
import subprocess
import sys
import threading
import time
from collections.abc import Iterator
from contextlib import contextmanager
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any

import pytest

from practice.paths import REPO_ROOT


def source(slug: str) -> bytes:
    return json.dumps(
        {
            "data": {
                "question": {
                    "questionId": "913",
                    "questionFrontendId": "LCR 913",
                    "titleSlug": slug,
                    "title": "Invented Widget",
                    "isPaidOnly": False,
                    "content": "<p>Example 1:</p><pre>Input: n = 7\nOutput: 14</pre>"
                    "<p>Example 2:</p><pre>Input: n = 0\nOutput: 0</pre>"
                    "<p>Constraints:</p><ul><li>"
                    "0 &lt;= n &lt;= 10<sup>3</sup></li></ul>",
                    "codeSnippets": [
                        {
                            "langSlug": "python3",
                            "code": "class Solution:\n"
                            "    def widget(self, n: int) -> int:\n        ",
                        }
                    ],
                }
            }
        }
    ).encode()


@contextmanager
def service(mode: str = "good") -> Iterator[tuple[str, list[tuple[str, float]]]]:
    requests: list[tuple[str, float]] = []

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, format: str, *args: Any) -> None:
            pass

        def do_POST(self) -> None:
            request = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
            slug = request["variables"]["titleSlug"]
            requests.append((slug, time.monotonic()))
            assert self.headers["Content-Type"] == "application/json"
            body = source(slug)
            status = 200
            if mode == "rate":
                status = 429
            elif mode == "redirect":
                status = 302
            elif mode == "large":
                body = b"x" * (5 * 1024 * 1024 + 1)
            elif mode == "json":
                body = b"not JSON"
            elif mode == "batch" and len(requests) == 2:
                body = b'{"data":{"question":null}}'
            self.send_response(status)
            if status == 302:
                self.send_header("Location", "/other")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever)
    thread.start()
    try:
        yield f"http://127.0.0.1:{server.server_port}/graphql", requests
    finally:
        server.shutdown()
        thread.join()
        server.server_close()


def command(output: Path, url: str, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [
            sys.executable,
            "tools/fetch_problem_facts.py",
            "--output",
            str(output),
            "--leetcode-url",
            url,
            "--delay",
            "0.15",
            *args,
        ],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )


def test_command_deduplicates_paces_and_preserves_provenance(tmp_path: Path) -> None:
    with service() as (url, requests):
        result = command(tmp_path, url, "widget-one", "widget-two", "widget-one")
    assert result.returncode == 0, result.stderr
    assert result.stderr == ""
    assert [slug for slug, _ in requests] == ["widget-one", "widget-two"]
    assert requests[1][1] - requests[0][1] >= 0.13
    facts = json.loads((tmp_path / "widget-one.json").read_text())
    assert len(facts["examples"]) == 2
    assert facts["constraints"] == ["0 <= n <= 10^3"]
    assert (
        facts["source"]["response_sha256"]
        == hashlib.sha256(source("widget-one")).hexdigest()
    )
    assert facts["source"]["graphql_url"] == url
    assert facts["source"]["fetched_at"]
    assert set(path.name for path in tmp_path.iterdir()) == {
        "widget-one.json",
        "widget-two.json",
    }


@pytest.mark.parametrize(
    ("mode", "message"),
    [
        ("rate", "429"),
        ("redirect", "redirect"),
        ("large", "byte limit"),
        ("json", "JSON"),
        ("batch", "unknown"),
    ],
)
def test_failures_preserve_prior_batch(tmp_path: Path, mode: str, message: str) -> None:
    prior = tmp_path / "widget-one.json"
    prior.write_text("unrelated prior bytes")
    with service(mode) as (url, requests):
        result = command(tmp_path, url, "widget-one", "widget-two")
    assert result.returncode == 1
    assert message in result.stderr
    assert "Traceback" not in result.stderr
    assert prior.read_text() == "unrelated prior bytes"
    assert not (tmp_path / "widget-two.json").exists()
    assert len(requests) == (2 if mode == "batch" else 1)


@pytest.mark.parametrize("delay", ["0", "-1", "nan", "inf"])
def test_interval_validation_before_http(tmp_path: Path, delay: str) -> None:
    with service() as (url, requests):
        result = command(tmp_path, url, "--delay", delay, "widget-one")
    assert result.returncode == 2
    assert "finite and positive" in result.stderr
    assert not requests


def test_refuses_tracked_destination_and_slug_traversal(tmp_path: Path) -> None:
    with service() as (url, requests):
        result = command(REPO_ROOT / "src", url, "widget-one")
        traversal = command(tmp_path, url, "../widget")
    assert result.returncode == 1
    assert traversal.returncode == 2
    assert not requests


def test_refuses_unrelated_existing_output(tmp_path: Path) -> None:
    prior = tmp_path / "widget-one.json"
    prior.write_text("unrelated prior bytes")
    with service() as (url, _):
        result = command(tmp_path, url, "widget-one")
    assert result.returncode == 1
    assert "existing" in result.stderr
    assert prior.read_text() == "unrelated prior bytes"
