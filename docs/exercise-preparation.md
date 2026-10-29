# Exercise preparation

How a problem becomes a committed, learner-facing exercise package, and how to
tell that it is ready. LeetCode 1 (Two Sum) is the worked example. LeetCode 217
(Contains Duplicate) follows the same layout with a boolean answer and the `exact`
checker.

## Pipeline

1. Verify the problem against `catalog/leetcode.json` and the live site. Record
   what was and was not seen in `readiness.json` under `verification`.
2. Write the package under `problems/<platform>-<id>/`:
   - `problem.json` and `tests.json` (the runner contract)
   - `starter.py`: a blank typed function that the runner reports as `stub`
   - `statement.md`: our own summary, constraints and examples, with a link to the source
   - `notes.md`: correctness and complexity notes, classed as a spoiler
   - `hints/0.md` and up, with `hints/index.json` giving each level's class,
     spoiler flag and whether it names the technique (only the last may)
   - `readiness.json`: the machine-readable record
3. Build the suite. Keep hand cases and seeded generated cases in a script under
   `tools/` with a brute-force oracle, and commit its output. `--check` fails if
   `tests.json` differs from a fresh build.
4. Preserve references with `practice sources add`: the upstream file unchanged,
   an adaptation that makes it runnable (registered as derived from upstream), and
   an original agent-written reference.
5. Record evidence with `practice sources validate ID --package DIR`. It runs the
   preserved file against the package and stores the result bound to the file's
   SHA-256 and the suite hash.
6. Run `practice readiness <platform> <id>`.

## Checklist mapping

| Requirement | Where it lives | Checked by |
| --- | --- | --- |
| Verified problem record | `statement.md`, `readiness.json` | readiness `record`, `files` |
| Blank typed starter | `starter.py` | readiness `starter`, integration test |
| Tests with checker | `tests.json`, `problem.json` | unit tests with an independent oracle |
| Correctness notes (spoiler) | `notes.md` | readiness `files` |
| Gradual classified hints | `hints/` | readiness `hints` |
| References and evidence | `references/` | readiness `references`, `evidence` |
| Platform acceptance | manifest `platform_acceptance` | stays `none` until you record it |

## Readiness criteria

`practice readiness` exits 0 when every check passes, 1 when any fails, and 3 when
the package cannot load. Checks: `package` (loads with cases), `record` (matches the
package), `starter` (is a stub), `files` (statement open, notes spoiler), `hints`
(at least four levels, classed, technique only last), `references` (upstream and
original listed, manifests verify), `evidence` (adapters and originals have a
passed, current validation on this suite), `blockers` (none listed). `--json` gives
the same report for tools. The report always shows platform acceptance, which is
`none` unless a person recorded a LeetCode verdict.

## Evidence and staleness

Local validation is not LeetCode acceptance. A passed local run is stored with the
code SHA-256 and the suite SHA-256. Change the code and the manifest hash no longer
matches (`sources verify` fails). Update the hash and the evidence is `stale` until
`sources validate` runs again. Change the suite and the evidence is for a different
suite, which readiness reports. Upstream files that cannot run as stored keep
validation `none`; the adapter carries the evidence.

## Adding the next problem

1. Copy the layout above to `problems/<platform>-<id>/` and fill it in.
2. Add a generator under `tools/` and a unit test that runs it with `--check`.
3. Add defective and alternate solutions under `tests/fixtures/` and tests that
   assert the outcome of each. Every defect must fail a named case.
4. Add references, run `sources validate`, then `readiness`.
5. Add an e2e test that drives the CLI in a subprocess with a temporary
   `PRACTICE_DIR` and no `--package` flag.

## When the platform cannot be reached

Step 1 needs the live problem. If it cannot be read, record what was checked
(the catalog snapshot, the preserved upstream file) under `verified`, record what
was taken from memory under `not_verified`, and add a line to `blockers`. The
readiness report then says `NOT READY` and names that blocker, even though every
other check passes. Clear it only after re-reading the signature, return type and
constraints and correcting the package to match. A person who has read the page may
supply those facts; record them as reported by that person, not as fetched.
LeetCode 217 was in this state until its owner confirmed the signature and
constraints.

## Known limits

The runner reports only total duration, not per-case timing, so a slow but correct
solution shows up as a longer run, or a timeout. The hidden LeetCode tests are not
available, so a local pass never proves a platform pass.
