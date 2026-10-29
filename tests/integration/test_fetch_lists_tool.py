# ABOUTME: Runs tools/fetch_lists.py against a real local HTTP server it can talk to.
# ABOUTME: A failed fetch must write nothing, and every limit must hold on the wire.

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

TOOL = REPO_ROOT / "tools" / "fetch_lists.py"
REVISION = "0123456789abcdef0123456789abcdef01234567"
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
            "paid_only": n == 4,
        }
        for n in range(1, 9)
    ],
}
REGISTRY: dict[str, Any] = {
    "schema_version": 1,
    "site_data": {
        "repository": "https://github.com/example/site",
        "revision": REVISION,
        "path": "data.json",
        "license": "MIT",
    },
    "lists": [
        {
            "id": "plan-a",
            "name": "Plan A",
            "kind": "leetcode_study_plan",
            "plan_slug": "plan-a",
            "size": 3,
        },
        {
            "id": "plan-b",
            "name": "Plan B",
            "kind": "leetcode_study_plan",
            "plan_slug": "plan-b",
            "size": 2,
        },
        {
            "id": "flagged",
            "name": "Flagged",
            "kind": "neetcode_site_data",
            "flag": "flagged",
            "size": 3,
        },
        {
            "id": "everything",
            "name": "Everything",
            "kind": "neetcode_site_data",
            "flag": "*",
            "size": 5,
        },
    ],
}


def plan(groups: list[tuple[str, list[int]]]) -> dict[str, Any]:
    return {
        "data": {
            "studyPlanV2Detail": {
                "slug": "x",
                "name": "x",
                "planSubGroups": [
                    {
                        "name": name,
                        "slug": name.lower(),
                        "questions": [
                            {
                                "titleSlug": f"problem-{n}",
                                "title": f"Problem {n}",
                                "questionFrontendId": str(n),
                                "paidOnly": n == 4,
                            }
                            for n in numbers
                        ],
                    }
                    for name, numbers in groups
                ],
            }
        }
    }


def row(n: int, pattern: str, **flags: bool) -> dict[str, Any]:
    return {
        "problem": f"Problem {n}",
        "pattern": pattern,
        "link": f"problem-{n}/",
        "code": f"{n:04d}-problem-{n}",
        **flags,
    }


PLANS = {
    "plan-a": plan([("Warm up", [2, 1]), ("Main", [3])]),
    "plan-b": plan([("Only group", [5, 4])]),
}
SITE_DATA = [
    row(1, "Arrays", flagged=True),
    row(2, "Arrays", flagged=True),
    row(3, "Strings"),
    row(5, "Strings", flagged=True),
    row(6, "Graphs"),
]


class Server(ThreadingHTTPServer):
    daemon_threads = True
    plans: dict[str, Any]
    site: bytes
    status: int
    redirect: bool
    oversize: bool
    garbage: bool
    times: list[float]


class Handler(BaseHTTPRequestHandler):
    def _send(
        self, status: int, body: bytes, extra: dict[str, str] | None = None
    ) -> None:
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        for key, value in (extra or {}).items():
            self.send_header(key, value)
        self.end_headers()
        self.wfile.write(body)

    def _common(self) -> bool:
        server = cast(Server, self.server)
        server.times.append(time.monotonic())
        if server.redirect:
            self._send(302, b"", {"Location": "http://127.0.0.1:9/elsewhere"})
            return True
        if server.status != 200:
            self._send(server.status, b'{"error": "nope"}')
            return True
        if server.oversize:
            self._send(200, b" " * (6 * 1024 * 1024))
            return True
        if server.garbage:
            self._send(200, b"<html>not json</html>")
            return True
        return False

    def do_POST(self) -> None:
        server = cast(Server, self.server)
        length = int(self.headers.get("Content-Length", "0"))
        request = json.loads(self.rfile.read(length))
        if self._common():
            return
        slug = request["variables"]["slug"]
        body = server.plans.get(slug, {"data": {"studyPlanV2Detail": None}})
        self._send(200, json.dumps(body).encode())

    def do_GET(self) -> None:
        server = cast(Server, self.server)
        if self._common():
            return
        self._send(200, server.site)

    def log_message(self, format: str, *args: Any) -> None:
        return  # Keep test output pristine.


@pytest.fixture
def server() -> Iterator[Server]:
    httpd = Server(("127.0.0.1", 0), Handler)
    httpd.plans = dict(PLANS)
    httpd.site = json.dumps(SITE_DATA).encode()
    httpd.status = 200
    httpd.redirect = httpd.oversize = httpd.garbage = False
    httpd.times = []
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    yield httpd
    httpd.shutdown()
    httpd.server_close()
    thread.join()


class Workspace:
    def __init__(self, root: Path, server: Server) -> None:
        self.root = root
        self.server = server
        self.catalog = root / "leetcode.json"
        self.registry = root / "list-sources.json"
        self.output = root / "lists"
        self.catalog.write_text(json.dumps(CATALOG), encoding="utf-8")
        self.registry.write_text(json.dumps(REGISTRY), encoding="utf-8")
        self.output.mkdir()

    @property
    def base(self) -> str:
        return f"http://127.0.0.1:{self.server.server_address[1]}"

    def run(
        self, *args: str, delay: str = "0", extra: list[str] | None = None
    ) -> subprocess.CompletedProcess[str]:
        command = [
            sys.executable,
            "-I",
            str(TOOL),
            "--registry",
            str(self.registry),
            "--catalog",
            str(self.catalog),
            "--output-dir",
            str(self.output),
            "--leetcode-url",
            f"{self.base}/graphql",
            "--site-data-url",
            f"{self.base}/site.json",
            "--delay",
            delay,
            "--retrieved-on",
            "2026-10-29",
            *args,
            *(extra or []),
        ]
        return subprocess.run(
            command, capture_output=True, text=True, check=False, timeout=60
        )

    def files(self) -> list[str]:
        return sorted(path.name for path in self.output.iterdir())

    def read(self, list_id: str) -> dict[str, Any]:
        loaded = json.loads((self.output / f"{list_id}.json").read_text("utf-8"))
        assert isinstance(loaded, dict)
        return loaded


@pytest.fixture
def work(tmp_path: Path, server: Server) -> Workspace:
    return Workspace(tmp_path, server)


def test_fetch_writes_one_valid_file_per_registered_list(work: Workspace) -> None:
    result = work.run("fetch")
    assert result.returncode == 0, result.stderr
    assert work.files() == [
        "everything.json",
        "flagged.json",
        "plan-a.json",
        "plan-b.json",
    ]
    assert "plan-a" in result.stdout and "everything" in result.stdout


def test_a_study_plan_keeps_its_order_groups_and_provenance(work: Workspace) -> None:
    assert work.run("fetch").returncode == 0
    data = work.read("plan-a")
    assert data["name"] == "Plan A" and data["size"] == 3
    assert [g["name"] for g in data["groups"]] == ["Warm up", "Main"]
    assert data["groups"][0]["problems"] == [
        {"id": 2, "slug": "problem-2"},
        {"id": 1, "slug": "problem-1"},
    ]
    source = data["source"]
    assert source["kind"] == "leetcode_study_plan"
    assert source["plan_slug"] == "plan-a"
    assert source["url"] == "https://leetcode.com/studyplan/plan-a/"
    assert source["retrieved_on"] == "2026-10-29"
    assert "no problem text" in source["note"]


def test_site_data_lists_group_by_pattern_in_file_order(work: Workspace) -> None:
    assert work.run("fetch").returncode == 0
    flagged = work.read("flagged")
    assert [g["name"] for g in flagged["groups"]] == ["Arrays", "Strings"]
    assert [p["id"] for g in flagged["groups"] for p in g["problems"]] == [1, 2, 5]
    source = flagged["source"]
    assert source["kind"] == "neetcode_site_data"
    assert source["revision"] == REVISION
    assert source["license"] == "MIT"
    assert source["flag"] == "flagged"
    assert source["url"].startswith("https://github.com/example/site/blob/")
    everything = work.read("everything")
    assert everything["size"] == 5
    assert "flag" in everything["source"] and everything["source"]["flag"] == "*"


def test_premium_problems_stay_in_the_list(work: Workspace) -> None:
    assert work.run("fetch").returncode == 0
    ids = [p["id"] for g in work.read("plan-b")["groups"] for p in g["problems"]]
    assert ids == [5, 4]  # Problem 4 is premium in the invented catalog.


def test_fetching_again_gives_byte_identical_files(work: Workspace) -> None:
    assert work.run("fetch").returncode == 0
    first = {name: (work.output / name).read_bytes() for name in work.files()}
    assert work.run("fetch").returncode == 0
    assert {name: (work.output / name).read_bytes() for name in work.files()} == first


def test_check_passes_when_nothing_changed(work: Workspace) -> None:
    assert work.run("fetch").returncode == 0
    result = work.run("fetch", extra=["--check"])
    assert result.returncode == 0, result.stderr
    assert "match" in result.stdout.lower()


def test_check_ignores_the_retrieval_date(work: Workspace) -> None:
    assert work.run("fetch").returncode == 0
    command_extra = ["--check"]
    result = work.run("fetch", extra=command_extra)
    assert result.returncode == 0
    data = work.read("plan-a")
    data["source"]["retrieved_on"] = "2020-01-01"
    (work.output / "plan-a.json").write_text(json.dumps(data), encoding="utf-8")
    assert work.run("fetch", extra=["--check"]).returncode == 0


def test_check_fails_and_names_the_list_when_the_source_changed(
    work: Workspace, server: Server
) -> None:
    assert work.run("fetch").returncode == 0
    server.plans["plan-a"] = plan([("Warm up", [2, 1]), ("Main", [6])])
    result = work.run("fetch", extra=["--check"])
    assert result.returncode == 1
    assert "plan-a" in result.stderr
    assert "plan-b" not in result.stderr


def test_an_unknown_plan_fails_and_writes_nothing(
    work: Workspace, server: Server
) -> None:
    del server.plans["plan-b"]
    result = work.run("fetch")
    assert result.returncode == 1
    assert "plan-b" in result.stderr and "no study plan" in result.stderr.lower()
    assert work.files() == []  # Not even the lists that fetched fine.


@pytest.mark.parametrize(
    ("setting", "message"),
    [
        ("status", "429"),
        ("redirect", "redirect"),
        ("oversize", "larger than"),
        ("garbage", "not valid JSON"),
    ],
)
def test_a_bad_response_fails_clearly_and_writes_nothing(
    work: Workspace, server: Server, setting: str, message: str
) -> None:
    if setting == "status":
        server.status = 429
    else:
        setattr(server, setting, True)
    result = work.run("fetch")
    assert result.returncode == 1
    assert message in result.stderr
    assert work.files() == []


def test_a_problem_missing_from_the_catalog_fails_and_writes_nothing(
    work: Workspace, server: Server
) -> None:
    server.plans["plan-a"] = plan([("Warm up", [2, 1]), ("Main", [31])])
    result = work.run("fetch")
    assert result.returncode == 1
    assert "plan-a" in result.stderr and "31" in result.stderr
    assert work.files() == []


def test_a_size_that_disagrees_with_the_registry_fails(
    work: Workspace, server: Server
) -> None:
    server.plans["plan-b"] = plan([("Only group", [5, 4, 3])])
    result = work.run("fetch")
    assert result.returncode == 1
    assert (
        "plan-b" in result.stderr and "declares 2 problems but has 3" in result.stderr
    )
    assert work.files() == []


def test_a_wrong_file_number_in_the_site_data_is_resolved_by_slug_with_a_warning(
    work: Workspace, server: Server
) -> None:
    rows = list(SITE_DATA)
    rows[3] = {**rows[3], "code": "9999-problem-5"}  # Slug says problem 5.
    server.site = json.dumps(rows).encode()
    result = work.run("fetch")
    assert result.returncode == 0, result.stderr
    ids = [p["id"] for g in work.read("flagged")["groups"] for p in g["problems"]]
    assert ids == [1, 2, 5]  # The catalog's id for the slug, not 9999.
    assert "9999" in result.stderr and "problem-5" in result.stderr
    assert "using the catalog" in result.stderr


def test_a_slug_the_catalog_does_not_know_still_fails(
    work: Workspace, server: Server
) -> None:
    rows = list(SITE_DATA)
    rows[3] = {**rows[3], "link": "no-such-problem/", "code": "0005-no-such-problem"}
    server.site = json.dumps(rows).encode()
    result = work.run("fetch")
    assert result.returncode == 1
    assert "no-such-problem" in result.stderr
    assert work.files() == []


def test_a_clean_run_prints_no_warning(work: Workspace) -> None:
    result = work.run("fetch")
    assert result.returncode == 0
    assert result.stderr == ""


def test_only_limits_the_run_to_the_named_lists(work: Workspace) -> None:
    result = work.run("fetch", extra=["--only", "plan-b"])
    assert result.returncode == 0, result.stderr
    assert work.files() == ["plan-b.json"]


def test_an_unknown_only_name_is_a_usage_error(work: Workspace) -> None:
    result = work.run("fetch", extra=["--only", "nope"])
    assert result.returncode == 2
    assert "nope" in result.stderr
    assert work.files() == []


def test_requests_to_leetcode_are_spaced_by_the_delay(
    work: Workspace, server: Server
) -> None:
    result = work.run("fetch", delay="0.4", extra=["--only", "plan-a", "plan-b"])
    assert result.returncode == 0, result.stderr
    assert len(server.times) == 2
    assert server.times[1] - server.times[0] >= 0.35


def test_plain_http_to_a_remote_host_is_refused_before_any_request(
    work: Workspace, server: Server
) -> None:
    command = [
        sys.executable,
        "-I",
        str(TOOL),
        "--registry",
        str(work.registry),
        "--catalog",
        str(work.catalog),
        "--output-dir",
        str(work.output),
        "--leetcode-url",
        "http://example.test/graphql",
        "--delay",
        "0",
        "fetch",
    ]
    result = subprocess.run(command, capture_output=True, text=True, timeout=60)
    assert result.returncode == 2
    assert "https" in result.stderr
    assert server.times == []
    assert work.files() == []


def test_files_the_registry_does_not_list_are_left_alone(work: Workspace) -> None:
    (work.output / "other.json").write_text("{}", encoding="utf-8")
    assert work.run("fetch").returncode == 0
    assert "other.json" in work.files()
    assert (work.output / "other.json").read_text(encoding="utf-8") == "{}"


def test_add_registers_and_fetches_a_new_study_plan(
    work: Workspace, server: Server
) -> None:
    server.plans["plan-c"] = plan([("Group", [7, 8])])
    result = work.run(
        "add",
        "--leetcode-plan",
        "plan-c",
        "--id",
        "plan-c",
        "--name",
        "Plan C",
        "--size",
        "2",
    )
    assert result.returncode == 0, result.stderr
    assert work.files() == ["plan-c.json"]
    registry = json.loads(work.registry.read_text(encoding="utf-8"))
    added = registry["lists"][-1]
    assert added == {
        "id": "plan-c",
        "name": "Plan C",
        "kind": "leetcode_study_plan",
        "plan_slug": "plan-c",
        "size": 2,
    }
    assert len(registry["lists"]) == len(REGISTRY["lists"]) + 1


def test_add_accepts_a_study_plan_address(work: Workspace, server: Server) -> None:
    server.plans["plan-c"] = plan([("Group", [7, 8])])
    result = work.run(
        "add",
        "--leetcode-plan",
        "https://leetcode.com/studyplan/plan-c/",
        "--id",
        "plan-c",
        "--name",
        "Plan C",
    )
    assert result.returncode == 0, result.stderr
    registry = json.loads(work.registry.read_text(encoding="utf-8"))
    assert registry["lists"][-1]["plan_slug"] == "plan-c"
    assert registry["lists"][-1]["size"] == 2  # Taken from what was fetched.


def test_add_of_a_plan_that_does_not_exist_changes_nothing(work: Workspace) -> None:
    before = work.registry.read_bytes()
    result = work.run(
        "add", "--leetcode-plan", "no-such-plan", "--id", "no-such", "--name", "No"
    )
    assert result.returncode == 1
    assert "no study plan" in result.stderr.lower()
    assert work.registry.read_bytes() == before
    assert work.files() == []


def test_add_refuses_an_id_that_is_already_registered(work: Workspace) -> None:
    before = work.registry.read_bytes()
    result = work.run(
        "add", "--leetcode-plan", "plan-b", "--id", "plan-a", "--name", "Again"
    )
    assert result.returncode == 2
    assert "already" in result.stderr
    assert work.registry.read_bytes() == before


def test_add_registers_a_flag_from_the_site_data(work: Workspace) -> None:
    result = work.run(
        "add", "--neetcode-flag", "flagged", "--id", "flagged-two", "--name", "Two"
    )
    assert result.returncode == 0, result.stderr
    assert work.read("flagged-two")["size"] == 3
