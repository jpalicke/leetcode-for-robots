# ABOUTME: Shared pytest fixtures that locate the Two Sum runner fixture package.
# ABOUTME: Also builds throwaway exercise packages and a real local upstream server.

import json
import shutil
import threading
from collections.abc import Callable, Iterator
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, cast

import pytest

FIXTURES = Path(__file__).resolve().parent / "fixtures"


@pytest.fixture
def two_sum_package() -> Path:
    return FIXTURES / "two_sum"


@pytest.fixture
def two_sum_solution() -> Callable[[str], Path]:
    def locate(name: str) -> Path:
        return FIXTURES / "two_sum_solutions" / f"{name}.py"

    return locate


@pytest.fixture
def make_package(tmp_path: Path) -> Callable[..., Path]:
    """Write a package directory; pass suite=None to leave out the test suite."""

    def build(metadata: dict[str, Any], suite: dict[str, Any] | None = None) -> Path:
        package = tmp_path / "package"
        package.mkdir()
        (package / "problem.json").write_text(json.dumps(metadata), encoding="utf-8")
        if suite is not None:
            (package / "tests.json").write_text(json.dumps(suite), encoding="utf-8")
        return package

    return build


@pytest.fixture
def leetcode_two_sum_package(tmp_path: Path, two_sum_package: Path) -> Path:
    """A copy of the Two Sum fixture identified as LeetCode problem 1."""
    package = tmp_path / "leetcode-1-package"
    shutil.copytree(two_sum_package, package)
    metadata_path = package / "problem.json"
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    metadata.update(platform="leetcode", id="1")
    metadata_path.write_text(json.dumps(metadata), encoding="utf-8")
    return package


class _UpstreamHTTPServer(ThreadingHTTPServer):
    daemon_threads = True
    files: dict[str, bytes]
    redirects: dict[str, str]


class _UpstreamHandler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:
        server = cast(_UpstreamHTTPServer, self.server)
        if self.path in server.redirects:
            self.send_response(302)
            self.send_header("Location", server.redirects[self.path])
            self.send_header("Content-Length", "0")
            self.end_headers()
            return
        body = server.files.get(self.path)
        if body is None:
            self.send_error(404)
            return
        self.send_response(200)
        self.send_header("Content-Type", "application/octet-stream")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format: str, *args: Any) -> None:
        return  # Keep test output pristine.


class UpstreamServer:
    """A real HTTP server on 127.0.0.1 that serves raw upstream file bytes."""

    def __init__(self, server: _UpstreamHTTPServer) -> None:
        self._server = server
        self.base_url = f"http://127.0.0.1:{server.server_address[1]}"

    def publish(self, revision: str, path: str, data: bytes) -> str:
        url_path = f"/{revision}/{path}"
        self._server.files[url_path] = data
        return f"{self.base_url}{url_path}"

    def redirect(self, revision: str, path: str, target: str) -> None:
        self._server.redirects[f"/{revision}/{path}"] = target


@pytest.fixture
def upstream_server() -> Iterator[UpstreamServer]:
    server = _UpstreamHTTPServer(("127.0.0.1", 0), _UpstreamHandler)
    server.files = {}
    server.redirects = {}
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield UpstreamServer(server)
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=10)
