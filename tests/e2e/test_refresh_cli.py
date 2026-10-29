# ABOUTME: Exercises catalog refresh through real CLI child processes and HTTP.
# ABOUTME: Verifies OS lock ownership, interruption recovery and clear error output.

from __future__ import annotations

import json
import subprocess
import sys
import threading
from collections.abc import Iterator
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import TYPE_CHECKING, Any, cast

import pytest

from practice.catalog import DEFAULT_CATALOG_PATH
from practice.catalog_refresh import refresh_catalog

if TYPE_CHECKING:
    from conftest import UpstreamServer
from tools.catalog_test_data import payload


def command(path: Path, source: str) -> list[str]:
    return [
        sys.executable,
        "-c",
        "from practice.cli import run; run()",
        "--catalog",
        str(path),
        "catalog",
        "refresh",
        "--source",
        source,
        "--json",
    ]


def test_cli_refresh_and_failure_are_json(
    tmp_path: Path, upstream_server: UpstreamServer
) -> None:
    path = tmp_path / "catalog.json"
    path.write_bytes(DEFAULT_CATALOG_PATH.read_bytes())
    source = upstream_server.publish("catalog", "all", json.dumps(payload()).encode())
    result = subprocess.run(
        command(path, source), capture_output=True, text=True, timeout=20
    )
    assert result.returncode == 0, result.stderr
    assert result.stderr == ""
    report = json.loads(result.stdout)
    assert report["ok"] is True
    assert report["added"] == report["changed"] == report["removed"] == []
    before = path.read_bytes()
    result = subprocess.run(
        command(path, "http://example.org/"), capture_output=True, text=True, timeout=20
    )
    assert result.returncode == 3
    assert result.stderr == ""
    assert "days old" in json.loads(result.stdout)["error"]
    assert "only https" in json.loads(result.stdout)["error"]
    assert path.read_bytes() == before


class ControlledServer(ThreadingHTTPServer):
    daemon_threads = True
    entered: threading.Event
    release: threading.Event
    body: bytes


class ControlledHandler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:
        server = cast(ControlledServer, self.server)
        if self.path == "/rate-limit":
            self.send_response(429)
            self.send_header("Content-Length", "0")
            self.end_headers()
            return
        server.entered.set()
        if not server.release.wait(15):
            return
        self.send_response(200)
        self.send_header("Content-Length", str(len(server.body)))
        self.end_headers()
        try:
            self.wfile.write(server.body)
        except (BrokenPipeError, ConnectionResetError, ConnectionAbortedError):
            pass  # A deliberately terminated client cannot receive the response.

    def log_message(self, format: str, *args: Any) -> None:
        return


@pytest.fixture
def controlled_server() -> Iterator[ControlledServer]:
    server = ControlledServer(("127.0.0.1", 0), ControlledHandler)
    server.entered = threading.Event()
    server.release = threading.Event()
    server.body = json.dumps(payload()).encode()
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield server
    finally:
        server.release.set()
        server.shutdown()
        server.server_close()
        thread.join(10)


def test_interrupted_writer_releases_lock_and_preserves_snapshot(
    tmp_path: Path, controlled_server: ControlledServer, upstream_server: UpstreamServer
) -> None:
    path = tmp_path / "catalog.json"
    path.write_bytes(DEFAULT_CATALOG_PATH.read_bytes())
    before = path.read_bytes()
    source = f"http://127.0.0.1:{controlled_server.server_address[1]}/blocked"
    with subprocess.Popen(
        command(path, source), stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True
    ) as child:
        try:
            assert controlled_server.entered.wait(10), (
                "writer did not reach HTTP acquisition"
            )
            second = subprocess.run(
                command(path, source), capture_output=True, text=True, timeout=10
            )
            assert second.returncode == 3
            assert "already running" in json.loads(second.stdout)["error"]
            assert second.stderr == ""
            assert path.read_bytes() == before
        finally:
            child.terminate()
            out, err = child.communicate(timeout=10)
        assert out == err == ""
    assert path.read_bytes() == before
    # A reserved partial stage left by an interrupted process is never promoted.
    stage = path.with_name("." + path.name + ".refresh-interrupted.tmp")
    stage.write_bytes(b'{"entries": [')
    healthy = upstream_server.publish("catalog", "all", json.dumps(payload()).encode())
    assert refresh_catalog(path, healthy)["changed"] == []
    assert stage.read_bytes() == b'{"entries": ['


def test_uncooperative_edit_during_fetch_is_not_overwritten(
    tmp_path: Path, controlled_server: ControlledServer
) -> None:
    path = tmp_path / "catalog.json"
    path.write_bytes(DEFAULT_CATALOG_PATH.read_bytes())
    source = f"http://127.0.0.1:{controlled_server.server_address[1]}/blocked"
    with subprocess.Popen(
        command(path, source), stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True
    ) as child:
        try:
            assert controlled_server.entered.wait(10)
            edited = path.read_bytes() + b"\n"
            path.write_bytes(edited)
            controlled_server.release.set()
            out, err = child.communicate(timeout=20)
        finally:
            if child.poll() is None:
                child.kill()
                child.communicate(timeout=10)
    assert child.returncode == 3
    assert err == ""
    assert "changed during refresh" in json.loads(out)["error"]
    assert path.read_bytes() == edited


def test_http_rate_limit_is_reported_without_write(
    tmp_path: Path, controlled_server: ControlledServer
) -> None:
    path = tmp_path / "catalog.json"
    path.write_bytes(DEFAULT_CATALOG_PATH.read_bytes())
    before = path.read_bytes()
    source = f"http://127.0.0.1:{controlled_server.server_address[1]}/rate-limit"
    result = subprocess.run(
        command(path, source), capture_output=True, text=True, timeout=20
    )
    assert result.returncode == 3
    assert result.stderr == ""
    assert "HTTP 429" in json.loads(result.stdout)["error"]
    assert path.read_bytes() == before


@pytest.mark.parametrize(
    "body", [b"[" * 2000 + b"]" * 2000, b'{"huge":' + b"1" * 5000 + b"}"]
)
def test_unparseable_old_snapshot_has_no_traceback(tmp_path: Path, body: bytes) -> None:
    path = tmp_path / "catalog.json"
    path.write_bytes(body)
    result = subprocess.run(
        command(path, "http://127.0.0.1:1/"), capture_output=True, text=True, timeout=20
    )
    assert result.returncode == 3
    assert result.stderr == ""
    assert "age unavailable" in json.loads(result.stdout)["error"]
    assert path.read_bytes() == body
