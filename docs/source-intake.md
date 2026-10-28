# Source intake: preserved references with provenance

`practice sources` keeps published reference code exactly as upstream wrote it,
with its license notice, and records where every byte came from. It is the one
intake path. It preserves and cites. It does not run, adapt or vouch for code.

Downloaded bytes are untrusted data. Intake stores and hashes them and never
executes them.

## Layout

```text
references/
  upstream/<source-id>/      bytes exactly as published, plus the license notice
  adaptations/<source-id>/   local changes made to an upstream file
  original/<source-id>/      code written here, with no upstream
  manifests/<source-id>.json one provenance record per entry
```

- Upstream files are never edited, normalized or converted. `.gitattributes`
  marks `/references/** -text`, so Git applies no line-ending conversion, and
  manifests are written with LF endings. A file with CRLF endings or no final
  newline stays that way.
- Adapters, wrappers and test harnesses never go in `upstream/`. An adaptation
  has its own entry with `derived_from` naming the upstream entry it changed and
  a `transformation` sentence saying how.
- A file under these folders that no manifest lists is a verification error
  (interpreter `__pycache__` folders are ignored).

## Manifest schema (version 1)

Strict JSON. Every field is required. Unknown fields are rejected.

| Field | Meaning |
| --- | --- |
| `schema_version` | `1` |
| `id` | lowercase letters, digits and hyphens; also the file name |
| `kind` | `upstream`, `adaptation` or `original` |
| `title`, `language` | display title; language such as `python` |
| `classification` | a content class (below) |
| `file` | `path` (relative to `references/`) and `sha256` of the preserved bytes |
| `license` | `identifier`, `terms`, `policy_note` and `notice` (`path`, `sha256`); `null` only for `original` |
| `derived_from`, `transformation` | set for adaptations, `null` otherwise |
| `acquisition` | `acquired_at`, `method`, `fetched_urls`, `actor`, `tool` (`name`, `version`) |
| `evidence` | `publication`, `platform_acceptance`, `local_validation` |

An upstream entry must carry a license and a notice file, hashed. An adaptation
repeats its upstream entry's license record exactly.

### Evidence stays in three separate fields

1. `publication`: `published` or `unpublished`, with `url`, `repository`, exact
   40 character `revision` and `path`. Branch names are not accepted as pins.
2. `platform_acceptance`: `none`, `claimed_by_upstream` or `verified_by_us`,
   with the platform and the evidence. It is only ever recorded. It is never
   inferred from publication, from a repository's contribution rules or from a
   local run.
3. `local_validation`: `none`, or a runner status with `code_sha256`, `run_at`,
   `suite_sha256`, `suite_version` and `runner`. It is bound to the SHA-256 of
   the exact code that ran. If the preserved code later changes, the evidence is
   reported **stale** and `verify` fails. It is never inherited by an adaptation
   or a translation.

Source intake does not claim an algorithm is correct. A new entry always starts
with acceptance `none` and validation `none`. `record_validation` in
`practice.sources` is the library hook that binds a real `practice run` result to
the preserved code. No command calls it yet.

### Acquisition evidence

`acquired_at` is a UTC timestamp with offset. `method` is `http_fetch` for
upstream, `local_adaptation` or `authored` otherwise, and must match `kind`.
`fetched_urls` lists the exact raw URLs requested. `actor` says who or what ran
the fetch. `tool` records this repository's tooling name and version
(`practice` and its package version). Fetching accepts `https` (or `http` on a
loopback address for tests), follows no redirects, and caps the size.

### Licenses

`identifier` is an SPDX style id and `terms` is a plain sentence of what the
license asks of us. These identifiers are treated as permissive and need no
extra note: `MIT`, `Apache-2.0`, `BSD-2-Clause`, `BSD-3-Clause`, `ISC`, `0BSD`
and `CC0-1.0`. Anything else, including CC BY-SA, CC BY-NC-SA, GPL and any
unrecognized identifier, is rejected unless `policy_note` explains why and how
the material may be used. The notice file itself is preserved byte for byte.

### Content classes

`practice.classification` owns the vocabulary. The tutor policy copies it and
`practice tutor check` fails if the two drift (see the
[tutor contract](tutor-contract.md)). Each class has a spoiler flag. Spoiler classes stay hidden in practice mode until
the agreed assistance level allows them.

| Class | Spoiler |
| --- | --- |
| `teaching_explanation` | no |
| `statement_summary` | no |
| `reference_solution` | yes |
| `hint` | yes |
| `algorithm_implementation` | yes (can reveal the intended technique) |
| `test_data` | yes (expected outputs reveal answers) |

Four more classes cover learner-private material. They are never published
sources, so `practice sources` does not accept them, but the tutor policy needs
them and they are all spoilers: `prior_attempt`, `session_notes`,
`recommendation_label` and `generated_context`.

## Commands

```text
uv run --locked practice sources add ID --repository URL --revision SHA \
    --path PATH --license-path PATH --license-id MIT --terms "..." \
    --classification reference_solution --title "..." [--policy-note "..."]
uv run --locked practice sources add-local ID --kind adaptation --file FILE \
    --derived-from UPSTREAM_ID --transformation "..." --classification ... --title ...
uv run --locked practice sources verify
uv run --locked practice sources show ID [--json]
uv run --locked practice sources list
```

`--references PATH` (before the subcommand) selects another references folder.
Exit codes: 0 success, 1 unknown source id, 2 usage error, 3 invalid or failing
sources (including a fetch failure, a tampered file and stale evidence).

`verify` checks the schema and required fields, rejects unknown fields,
re-hashes the code and every notice, requires adaptations to point at an
existing upstream entry, requires unlisted files to be absent, and reports stale
validation. It prints every problem it finds.

`show` verifies the entry and prints its citation record. `citation()` in
`practice.sources` returns the same record for downstream exports: title, url,
revision, license, classification, spoiler flag and hashes.

## How to add a source

1. Pick the exact file and a full commit SHA from the upstream repository. Never
   a branch or tag. Select one file at a time; there is no bulk import.
2. Read the license that applies to that file and choose the class.
3. Run `practice sources add` with the upstream repository, SHA, file path and
   license path. Today only `https://github.com/OWNER/REPO` URLs derive a raw
   download address; `--raw-base` overrides it.
4. Run `practice sources verify`, then commit `references/`.
5. Keep any wrapper or fix as a separate `add-local` entry. Never edit the
   upstream copy.

The committed test `tests/e2e/test_committed_references.py` re-hashes the
demonstration file, compares it with upstream's own Git blob ids, checks
`.gitattributes`, and compares Git's view of the file with the bytes on disk.

## The demonstration import

One file only: the NeetCode solution to LeetCode 1 Two Sum in Python, from
`neetcode-gh/leetcode` (MIT), pinned to commit
`8fed5f7daa6a517e375a0562d876e4a72dfdafb8`, path `python/0001-two-sum.py`, with
the repository `LICENSE` from the same commit. Its platform acceptance and
local validation are both `none`.
