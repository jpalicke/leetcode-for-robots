# ABOUTME: Checks knowledge chunk identity independently of mutable content hashes.
# ABOUTME: Uses real byte strings to cover bounded chunks and byte preservation.

from practice.knowledge import _document


def test_chunk_identity_and_bytes() -> None:
    raw = ("λ\r\n" * 4000).encode("utf-8")
    doc = _document(
        "leetcode", "1", "python", "statement", "statement_summary", raw, "default"
    )
    changed = _document(
        "leetcode",
        "1",
        "python",
        "statement",
        "statement_summary",
        b"different",
        "default",
    )
    assert doc["id"] == changed["id"]
    assert doc["chunks"][0]["id"] == changed["chunks"][0]["id"]
    assert doc["content_sha256"] != changed["content_sha256"]
    assert all(len(c["text"]) <= 2000 for c in doc["chunks"])
    assert "".join(c["text"] for c in doc["chunks"]).encode("utf-8") == raw
