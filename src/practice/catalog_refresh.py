# ABOUTME: Validates upstream catalog metadata and atomically publishes refreshes.
# ABOUTME: Keeps durable coverage reconciliation evidence in the catalog envelope.

import json
import os
import sys
import tempfile
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import asdict
from datetime import date
from pathlib import Path
from typing import Any

from practice.catalog import Catalog, CatalogError, parse_catalog
from practice.source_fetch import FetchError, fetch_url

DEFAULT_SOURCE = "https://leetcode.com/api/problems/all/"


def parse_response(data: object, source: str) -> Catalog:
    if not isinstance(data, dict):
        raise CatalogError("response must be a JSON object")
    if data.get("error") or data.get("errors"):
        raise CatalogError("catalog endpoint returned an error response")
    rows = data.get("stat_status_pairs")
    if not isinstance(rows, list) or not rows:
        raise CatalogError("stat_status_pairs must be a non-empty list")
    if "num_total" in data:
        total = data["num_total"]
        if type(total) is not int or total < 1 or total != len(rows):
            raise CatalogError(
                "num_total must be a positive integer matching all response rows"
            )
    entries = []
    for index, row in enumerate(rows):
        if not isinstance(row, dict) or not isinstance(row.get("stat"), dict):
            raise CatalogError(f"response row {index}: stat must be an object")
        stat = row["stat"]
        difficulty = row.get("difficulty")
        level = difficulty.get("level") if isinstance(difficulty, dict) else None
        if type(level) is not int or level not in (1, 2, 3):
            raise CatalogError(
                f"response row {index}: difficulty.level must be 1, 2 or 3"
            )
        entries.append(
            {
                "platform": "leetcode",
                "frontend_question_id": stat.get("frontend_question_id"),
                "question_id": stat.get("question_id"),
                "title": stat.get("question__title"),
                "slug": stat.get("question__title_slug"),
                "difficulty": ("easy", "medium", "hard")[level - 1],
                "paid_only": row.get("paid_only"),
            }
        )
    return parse_catalog(
        {
            "platform": "leetcode",
            "source_url": source,
            "fetched_on": date.today().isoformat(),
            "entries": entries,
        }
    )


def catalog_diff(before: Catalog, after: Catalog) -> dict[str, Any]:
    old = {e.identity: e for e in before.entries}
    current = {e.identity: e for e in after.entries}
    result: dict[str, Any] = {"added": [], "changed": [], "removed": []}
    for identity in sorted(old.keys() | current.keys()):
        left, right = old.get(identity), current.get(identity)
        if left == right:
            continue
        kind = "added" if left is None else "removed" if right is None else "changed"
        left_fields = asdict(left) if left else None
        right_fields = asdict(right) if right else None
        result[kind].append(
            {
                "platform": identity[0],
                "frontend_question_id": identity[1],
                "before": left_fields,
                "after": right_fields,
                "changed_fields": [
                    key
                    for key in (right_fields or left_fields or {})
                    if left_fields is None
                    or right_fields is None
                    or left_fields[key] != right_fields[key]
                ],
            }
        )
    return result


def _pending(data: dict[str, Any]) -> list[dict[str, Any]]:
    if "refresh" not in data:
        return []
    metadata = data["refresh"]
    if (
        not isinstance(metadata, dict)
        or type(metadata.get("schema_version")) is not int
        or metadata.get("schema_version") != 1
    ):
        raise CatalogError("refresh metadata has an unsupported schema_version")
    pending = metadata.get("pending_coverage")
    if not isinstance(pending, list):
        raise CatalogError("refresh.pending_coverage must be a list")
    seen: set[tuple[str, int]] = set()
    for item in pending:
        if not isinstance(item, dict):
            raise CatalogError("pending coverage item must be an object")
        if (
            item.get("platform") != "leetcode"
            or type(item.get("frontend_question_id")) is not int
            or item["frontend_question_id"] < 1
        ):
            raise CatalogError(
                "pending coverage identity must be leetcode and a positive integer"
            )
        fields = item.get("changed_fields")
        if (
            not isinstance(fields, list)
            or not fields
            or any(
                not isinstance(f, str)
                or f
                not in {
                    "platform",
                    "frontend_question_id",
                    "question_id",
                    "title",
                    "slug",
                    "difficulty",
                    "paid_only",
                }
                for f in fields
            )
        ):
            raise CatalogError("pending coverage changed_fields must name entry fields")
        reasons = item.get("reasons")
        if (
            not isinstance(reasons, list)
            or not reasons
            or any(
                not isinstance(reason, str)
                or reason not in ("added", "changed", "removed")
                for reason in reasons
            )
        ):
            raise CatalogError("pending coverage reasons must name catalog changes")
        original, latest = item.get("before"), item.get("after")
        if original is None and latest is None:
            raise CatalogError("pending coverage item needs before or after evidence")
        for entry in (original, latest):
            if entry is not None:
                parsed = parse_catalog({**data, "entries": [entry]}).entries[0]
                if (parsed.platform, parsed.frontend_question_id) != (
                    item.get("platform"),
                    item.get("frontend_question_id"),
                ):
                    raise CatalogError(
                        "pending coverage identity differs from evidence"
                    )
        identity = (item["platform"], item["frontend_question_id"])
        if identity in seen:
            raise CatalogError("duplicate pending coverage identity")
        seen.add(identity)
    return pending


@contextmanager
def refresh_lock(path: Path) -> Iterator[None]:
    # Keep the lock inode: deleting it could let writers lock different files.
    with path.with_name(path.name + ".refresh.lock").open("a+b") as stream:
        if stream.tell() == 0:
            stream.write(b"\0")
            stream.flush()
        stream.seek(0)
        try:
            if sys.platform == "win32":
                import msvcrt

                msvcrt.locking(stream.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                import fcntl

                fcntl.flock(stream.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError as error:
            raise CatalogError(
                "catalog refresh is already running; retry after it exits"
            ) from error
        try:
            yield
        finally:
            stream.seek(0)
            if sys.platform == "win32":
                import msvcrt

                msvcrt.locking(stream.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                import fcntl

                fcntl.flock(stream.fileno(), fcntl.LOCK_UN)


def refresh_catalog(path: Path, source: str = DEFAULT_SOURCE) -> dict[str, Any]:
    try:
        path = path.resolve()
        with refresh_lock(path):
            return _refresh_locked(path, source)
    except (OSError, ValueError, UnicodeError, FetchError, RecursionError) as error:
        raise CatalogError(
            f"catalog refresh failed; existing snapshot preserved: {error}"
        ) from error


def _refresh_locked(path: Path, source: str) -> dict[str, Any]:
    original = path.read_bytes()
    data = json.loads(original)
    before = parse_catalog(data)
    if before.platform != "leetcode":
        raise CatalogError("refresh requires a LeetCode catalog")
    pending = _pending(data)
    after = parse_response(json.loads(fetch_url(source)), source)
    diff = catalog_diff(before, after)
    accumulated = {(p["platform"], p["frontend_question_id"]): p for p in pending}
    for kind in ("added", "changed", "removed"):
        for change in diff[kind]:
            identity = (change["platform"], change["frontend_question_id"])
            if identity not in accumulated:
                if kind != "added":
                    accumulated[identity] = {**change, "reasons": [kind]}
                continue
            # Preserve the original mapping evidence and the latest observed state.
            prior = accumulated[identity]
            accumulated[identity] = {
                **prior,
                "after": change["after"],
                "changed_fields": sorted(
                    set(prior["changed_fields"]) | set(change["changed_fields"])
                ),
                "reasons": sorted(set(prior["reasons"]) | {kind}),
            }
    report = {
        "schema_version": 1,
        **diff,
        "pending_coverage": [accumulated[k] for k in sorted(accumulated)],
    }
    envelope = {
        **data,
        "platform": after.platform,
        "source_url": after.source_url,
        "fetched_on": after.fetched_on,
        "entries": [asdict(e) for e in sorted(after.entries, key=lambda e: e.identity)],
        "refresh": report,
    }
    serialized = _serialize(envelope)
    handle, name = tempfile.mkstemp(
        dir=path.parent, prefix=f".{path.name}.refresh-", suffix=".tmp"
    )
    temporary = Path(name)
    try:
        with os.fdopen(handle, "wb") as stream:
            stream.write(serialized)
            stream.flush()
            os.fsync(stream.fileno())
        staged = json.loads(temporary.read_bytes())
        parse_catalog(staged)
        _pending(staged)
        if path.read_bytes() != original:
            raise CatalogError(
                "catalog changed during refresh; retry with the current snapshot"
            )
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)
    return report


def _serialize(envelope: dict[str, Any]) -> bytes:
    # Keep each catalog entry on one line, matching the committed snapshot style.
    head = {key: value for key, value in envelope.items() if key != "entries"}
    lines = [
        json.dumps(head, ensure_ascii=False, indent=2, allow_nan=False)[:-2] + ",",
        '  "entries": [',
    ]
    lines.append(
        ",\n".join(
            "    " + json.dumps(entry, ensure_ascii=False, allow_nan=False)
            for entry in envelope["entries"]
        )
    )
    lines.extend(["  ]", "}", ""])
    return "\n".join(lines).encode("utf-8")
