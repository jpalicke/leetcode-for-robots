# Catalog refresh

Refresh metadata from the unofficial LeetCode discovery endpoint:

```text
uv run --locked practice catalog refresh
uv run --locked practice --catalog .scratch/leetcode.json catalog refresh --json
uv run --locked practice --catalog .scratch/leetcode.json catalog refresh --source http://127.0.0.1:13337/all --json
```

Copy the committed `catalog/leetcode.json` to `.scratch/leetcode.json` before
trying the scratch example. An existing valid LeetCode snapshot is required.
The command updates only that catalog. Exercise packages, reference files,
learner attempts/history, curated lists and curriculum mappings are untouched.

The default source is `https://leetcode.com/api/problems/all/`. `--source` accepts
HTTPS or HTTP on localhost, 127.0.0.1 or ::1 for real local-server tests. Redirects
are refused; each HTTP operation has a 30-second socket timeout and downloads
are limited to 5 MiB. HTTP failures, including 429, are reported without retries.
This endpoint was discovered for metadata acquisition and is not a supported or
guaranteed API. Availability, access policies and response shape may change.
It supplies identifiers, title, slug, difficulty and premium status, not statements,
solutions or platform acceptance evidence. A successful response does not establish
that every platform problem is exposed by this endpoint.

Every response row must validate. `stat_status_pairs` must be nonempty; when
`num_total` is present it must be a positive integer equal to the row count.
Both `stat.frontend_question_id` and `stat.question_id` must be positive integers;
booleans, numeric strings and fractional numbers are rejected. Difficulty levels
must be the integers 1, 2 or 3, and `paid_only` must be a JSON boolean. Nothing is
silently filtered, including premium, hidden or specialized entries. Translation
then uses the same `parse_catalog` validation as search, including unique frontend
IDs and slugs. There is no permanent minimum count based on the discovery snapshot.

A refresh locks a persistent sibling `<catalog>.refresh.lock` with an OS lock,
reads and validates the old snapshot, fetches and validates all replacement rows,
and prepares the complete diff and reconciliation state. It serializes entries
in identity order, one per line, to an exclusively created sibling temporary file,
flushes and fsyncs it, and validates the staged artifact before `os.replace`.
Snapshot and refresh metadata publish in that single atomic replacement.
Other refresh writers fail clearly while the lock is held. OS process termination
releases the lock; the persistent lock file alone does not mean a writer is active.
A final byte comparison refuses to overwrite an observed external edit. Editors
that ignore the lock can still race after that comparison; this is not a general
transaction protocol for arbitrary writers or a power-loss durability guarantee.

Fetch, JSON, schema, serialization and write failures leave the old snapshot
byte-for-byte unchanged. Errors report its fetch date and age, or explain that
age is unavailable when the old snapshot cannot be validated. Normal failures
remove only the temporary file created by that invocation. An abruptly terminated
writer can leave an ignored `.NAME.refresh-UNIQUE.tmp` sibling; it is never loaded,
auto-promoted or deleted by a later refresh. Unrelated siblings are untouched.

Successful JSON has `ok: true`, `schema_version: 1`, `added`, `changed`, `removed`
and `pending_coverage`; failure JSON has `ok: false` and `error`. JSON goes to
stdout with no diagnostic stderr. Exit 0 means published, 3 means invalid input,
fetch or persistence failure, and argparse uses 2 for command usage errors.
Human output shows the counts, each change and the pending coverage count.

The catalog stores the successful report under top-level `refresh`. Diff identity
is `(platform, frontend_question_id)`, never internal `question_id`. Each diff
item has that identity, full `before`/`after` entry objects (including both IDs),
and `changed_fields`. Added entries have null `before`; removed entries have null
`after`. Search reads the entries and tolerates the extra envelope metadata.

Changed and removed identities enter `refresh.pending_coverage` for coverage
mapping #15. Each pending item retains the earliest unresolved `before`, the
latest observed `after`, the union of affected `changed_fields`, and sorted
`reasons` (`changed`, `removed`, or `added` for a pending identity that reappears).
A later no-op refresh has empty diff arrays but retains these flags. Removal and
reappearance never clear a flag, even if fields revert to their original values.
This command has no acknowledgement or clearing action; #15 owns reconciliation.
Pending metadata is validated before refresh and again from staging, so corrupt
or unsupported pending state cannot be silently discarded.

## Verification record: 2026-10-28

An initial live request to the default endpoint returned 4,096 rows, including
788 premium entries. The finished response translator validated that captured
payload and found no added, changed or removed entries against the committed
snapshot. The raw response stays in ignored scratch storage.

Two later invocations of the finished CLI against the same live endpoint returned
HTTP 403 and exit 3. Both reported the existing snapshot's age and preserved its
bytes; the committed catalog also remained identical to Git, and no learner state
was created. No access settings were changed. Successful acquisition and atomic
publication were verified through real loopback HTTP servers. Successful live
publication is not claimed for those refused requests.
