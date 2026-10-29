# ABOUTME: Exercises refresh over a real loopback server and real catalog files.
# ABOUTME: Checks durable diffs and byte preservation under acquisition failures.

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import TYPE_CHECKING

import pytest

from practice.catalog import DEFAULT_CATALOG_PATH, CatalogError, load_catalog
from practice.catalog_refresh import refresh_catalog

if TYPE_CHECKING:
    from conftest import UpstreamServer
from tools.catalog_test_data import payload


def snapshot(tmp_path: Path) -> Path:
    path = tmp_path / "leetcode.json"
    path.write_bytes(DEFAULT_CATALOG_PATH.read_bytes())
    return path


def test_added_changed_removed_and_noop_retain_pending(
    tmp_path: Path, upstream_server: UpstreamServer
) -> None:
    path = snapshot(tmp_path)
    original = load_catalog(path)
    data = payload()
    removed = data["stat_status_pairs"].pop()
    changed = data["stat_status_pairs"][0]
    changed["stat"]["question__title"] += " revised"
    added = json.loads(json.dumps(removed))
    added["stat"].update(
        frontend_question_id=99001,
        question_id=88001,
        question__title_slug="catalog-refresh-test",
    )
    data["stat_status_pairs"].append(added)
    sentinels = [
        tmp_path / name
        for name in ("history.jsonl", "exercise.py", "lists.json", "curriculum.json")
    ]
    for sentinel in sentinels:
        sentinel.write_bytes(b"preserve me\n")
    source = upstream_server.publish("catalog", "all", json.dumps(data).encode())
    report = refresh_catalog(path, source)
    assert len(report["added"]) == len(report["changed"]) == len(report["removed"]) == 1
    assert report["added"][0]["after"]["question_id"] == 88001
    assert report["added"][0]["frontend_question_id"] == 99001
    assert report["changed"][0]["changed_fields"] == ["title"]
    assert (
        report["removed"][0]["before"]["question_id"] == removed["stat"]["question_id"]
    )
    assert len(load_catalog(path).entries) == len(original.entries)
    pending = report["pending_coverage"]
    assert len(pending) == 2
    again = refresh_catalog(path, source)
    assert again["added"] == again["changed"] == again["removed"] == []
    assert again["pending_coverage"] == pending
    assert json.loads(path.read_bytes())["refresh"] == again
    published = path.read_bytes()
    data["stat_status_pairs"].reverse()
    source = upstream_server.publish("catalog", "all", json.dumps(data).encode())
    assert refresh_catalog(path, source) == again
    assert path.read_bytes() == published
    assert all(p.read_bytes() == b"preserve me\n" for p in sentinels)


@pytest.mark.parametrize("body", [b"{", b"null", b'{"stat_status_pairs":[]}', b"\xff"])
def test_invalid_response_preserves_bytes(
    tmp_path: Path, upstream_server: UpstreamServer, body: bytes
) -> None:
    path = snapshot(tmp_path)
    before = path.read_bytes()
    source = upstream_server.publish("catalog", "bad", body)
    with pytest.raises(CatalogError):
        refresh_catalog(path, source)
    assert path.read_bytes() == before


def test_duplicates_are_not_dropped(
    tmp_path: Path, upstream_server: UpstreamServer
) -> None:
    path = snapshot(tmp_path)
    before = path.read_bytes()
    data = payload()
    data["stat_status_pairs"].append(data["stat_status_pairs"][0])
    source = upstream_server.publish("catalog", "duplicate", json.dumps(data).encode())
    with pytest.raises(CatalogError, match="duplicate"):
        refresh_catalog(path, source)
    assert path.read_bytes() == before


def test_bad_old_snapshot_is_not_replaced(
    tmp_path: Path, upstream_server: UpstreamServer
) -> None:
    path = tmp_path / "leetcode.json"
    path.write_bytes(b"{invalid old snapshot")
    source = upstream_server.publish("catalog", "valid", json.dumps(payload()).encode())
    with pytest.raises(CatalogError):
        refresh_catalog(path, source)
    assert path.read_bytes() == b"{invalid old snapshot"


def test_redirect_and_oversize_preserve_snapshot(
    tmp_path: Path, upstream_server: UpstreamServer
) -> None:
    path = snapshot(tmp_path)
    before = path.read_bytes()
    upstream_server.redirect("catalog", "redirect", "https://example.org/")
    with pytest.raises(CatalogError, match="redirect"):
        refresh_catalog(path, upstream_server.base_url + "/catalog/redirect")
    source = upstream_server.publish("catalog", "large", b" " * (5 * 1024 * 1024 + 1))
    with pytest.raises(CatalogError, match="byte limit"):
        refresh_catalog(path, source)
    assert path.read_bytes() == before


def test_serialization_failure_preserves_snapshot(
    tmp_path: Path, upstream_server: UpstreamServer
) -> None:
    path = snapshot(tmp_path)
    data = json.loads(path.read_bytes())
    data["unserializable"] = float("nan")
    path.write_text(json.dumps(data), encoding="utf-8")
    before = path.read_bytes()
    source = upstream_server.publish("catalog", "valid", json.dumps(payload()).encode())
    with pytest.raises(CatalogError):
        refresh_catalog(path, source)
    assert path.read_bytes() == before


def test_existing_sibling_is_not_deleted(
    tmp_path: Path, upstream_server: UpstreamServer
) -> None:
    path = snapshot(tmp_path)
    unrelated = path.with_name(path.name + ".refresh.tmp")
    unrelated.write_bytes(b"unrelated sibling must survive")
    source = upstream_server.publish("catalog", "valid", json.dumps(payload()).encode())
    refresh_catalog(path, source)
    assert unrelated.read_bytes() == b"unrelated sibling must survive"


def test_pending_retains_original_and_latest_evidence(
    tmp_path: Path, upstream_server: UpstreamServer
) -> None:
    path = snapshot(tmp_path)
    data = payload()
    identity = data["stat_status_pairs"][0]["stat"]["frontend_question_id"]
    data["stat_status_pairs"][0]["stat"]["question__title"] += " changed"
    source = upstream_server.publish("catalog", "valid", json.dumps(data).encode())
    first = refresh_catalog(path, source)["pending_coverage"][0]
    removed = data["stat_status_pairs"].pop(0)
    source = upstream_server.publish("catalog", "valid", json.dumps(data).encode())
    final = refresh_catalog(path, source)["pending_coverage"][0]
    assert final["frontend_question_id"] == identity
    assert final["before"] == first["before"]
    assert final["after"] is None
    assert final["reasons"] == ["changed", "removed"]
    data["stat_status_pairs"].append(removed)
    source = upstream_server.publish("catalog", "valid", json.dumps(data).encode())
    reappeared = refresh_catalog(path, source)["pending_coverage"][0]
    assert reappeared["before"] == first["before"]
    assert reappeared["after"] == first["after"]
    assert reappeared["reasons"] == ["added", "changed", "removed"]


@pytest.mark.skipif(os.name != "nt", reason="Windows sharing violation")
def test_blocked_replace_preserves_snapshot_and_cleans_own_stage(
    tmp_path: Path, upstream_server: UpstreamServer
) -> None:
    path = snapshot(tmp_path)
    before = path.read_bytes()
    source = upstream_server.publish("catalog", "all", json.dumps(payload()).encode())
    with path.open("rb"):
        with pytest.raises(CatalogError, match="preserved"):
            refresh_catalog(path, source)
    assert path.read_bytes() == before
    assert list(tmp_path.glob(".*.refresh-*.tmp")) == []


@pytest.mark.parametrize(
    "metadata",
    [
        None,
        {},
        {"schema_version": True, "pending_coverage": []},
        {"schema_version": 1, "pending_coverage": [None]},
    ],
)
def test_invalid_pending_metadata_refuses_overwrite(
    tmp_path: Path, upstream_server: UpstreamServer, metadata: object
) -> None:
    path = snapshot(tmp_path)
    data = json.loads(path.read_bytes())
    data["refresh"] = metadata
    path.write_text(json.dumps(data), encoding="utf-8")
    before = path.read_bytes()
    source = upstream_server.publish("catalog", "all", json.dumps(payload()).encode())
    with pytest.raises(CatalogError, match="refresh|coverage"):
        refresh_catalog(path, source)
    assert path.read_bytes() == before
