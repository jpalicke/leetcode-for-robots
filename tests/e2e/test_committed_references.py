# ABOUTME: Offline checks of the committed NeetCode reference against git's own view.
# ABOUTME: Proves the preserved bytes are unchanged, unconverted and fully cited.

import hashlib
import subprocess

import pytest

from practice.paths import REFERENCES_DIR, REPO_ROOT
from practice.source_manifest import validation_state
from practice.sources import citation, load_manifest, verify_references

SOURCE_ID = "neetcode-leetcode-0001-two-sum-python"
REVISION = "8fed5f7daa6a517e375a0562d876e4a72dfdafb8"
# Git blob ids reported by GitHub for these paths at REVISION. They come from
# upstream, not from this repository, so they are an independent oracle.
UPSTREAM_BLOB_IDS = {
    "0001-two-sum.py": "e3eb994d333a15272ff4eec194f7bd2f0e2911ed",
    "LICENSE": "144c6f237c2c9a19404bd1def098172a9fc1c7c3",
}
FOLDER = REFERENCES_DIR / "upstream" / SOURCE_ID


def git(*args: str) -> str:
    result = subprocess.run(
        ["git", *args],
        capture_output=True,
        text=True,
        encoding="utf-8",
        cwd=REPO_ROOT,
        timeout=60,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    return result.stdout.strip()


def relative(name: str) -> str:
    return (FOLDER / name).relative_to(REPO_ROOT).as_posix()


def test_committed_references_verify_offline() -> None:
    report = verify_references(REFERENCES_DIR)
    assert report.problems == []
    assert SOURCE_ID in report.verified


@pytest.mark.parametrize("name", sorted(UPSTREAM_BLOB_IDS))
def test_bytes_on_disk_match_the_upstream_git_blob(name: str) -> None:
    data = (FOLDER / name).read_bytes()
    blob = hashlib.sha1(b"blob %d\0" % len(data) + data).hexdigest()
    assert blob == UPSTREAM_BLOB_IDS[name]


@pytest.mark.parametrize("name", sorted(UPSTREAM_BLOB_IDS))
def test_gitattributes_leaves_upstream_files_unconverted(name: str) -> None:
    attribute = git("check-attr", "text", "--", relative(name))
    assert attribute.endswith("text: unset")


@pytest.mark.parametrize("name", sorted(UPSTREAM_BLOB_IDS))
def test_git_would_store_exactly_the_bytes_on_disk(name: str) -> None:
    path = relative(name)
    filtered = git("hash-object", "--path", path, str(FOLDER / name))
    raw = git("hash-object", "--no-filters", str(FOLDER / name))
    assert filtered == raw == UPSTREAM_BLOB_IDS[name]


@pytest.mark.parametrize("name", sorted(UPSTREAM_BLOB_IDS))
def test_the_tracked_blob_is_the_upstream_blob(name: str) -> None:
    entry = git("ls-files", "--stage", "--", relative(name))
    assert entry, f"{relative(name)} is not tracked or staged"
    mode, blob, _stage = entry.split("\t")[0].split()
    assert mode == "100644"
    assert blob == UPSTREAM_BLOB_IDS[name]


def test_the_citation_is_complete_and_claims_no_validation() -> None:
    cited = citation(REFERENCES_DIR, SOURCE_ID)
    assert cited.revision == REVISION
    assert cited.path == "python/0001-two-sum.py"
    assert cited.repository == "https://github.com/neetcode-gh/leetcode"
    assert cited.license_identifier == "MIT"
    assert cited.classification == "reference_solution"
    assert cited.spoiler is True
    assert cited.platform_acceptance == "none"
    assert cited.local_validation == "none"
    assert cited.notice_sha256 is not None


def test_the_manifest_records_how_the_bytes_were_acquired() -> None:
    manifest = load_manifest(REFERENCES_DIR, SOURCE_ID)
    assert manifest.kind == "upstream"
    assert manifest.acquisition.method == "http_fetch"
    assert all(
        url.startswith(
            f"https://raw.githubusercontent.com/neetcode-gh/leetcode/{REVISION}/"
        )
        for url in manifest.acquisition.fetched_urls
    )
    assert manifest.acquisition.tool.name == "practice"
    assert validation_state(manifest) == "none"
