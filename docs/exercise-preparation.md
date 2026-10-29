# Exercise preparation

How a problem becomes a committed, learner-facing exercise package, and how to
tell that it is ready. LeetCode 1 (Two Sum) is the worked example. LeetCode 217
(Contains Duplicate), 242 (Valid Anagram) and 20 (Valid Parentheses) follow the same
layout with a boolean answer and the `exact` checker; 242 takes two string arguments.
704 (Binary Search) and 121 (Best Time to Buy and Sell Stock) use `exact` on an
integer. Packages 20, 704 and 121 are those whose page facts were fetched from the
live endpoint rather than reported by a person, and each `readiness.json` says which.

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
LeetCode 217 was in this state until its owner confirmed the signature,
constraints and examples, and so was LeetCode 242.

## Fetching problem facts

```text
uv run --locked python tools/fetch_problem_facts.py contains-duplicate valid-anagram
uv run --locked python tools/fetch_problem_facts.py contains-duplicate --output .scratch/facts-review --delay 2
```

The tool sends one GraphQL POST per distinct slug in requested order, with at least
one second between request starts by default. `--delay` must be finite and positive.
It saves one JSON per slug with the Python3 `Solution` method signature, constraints,
every numbered example's input/output strings and optional explanation. It parses
HTML and Python syntax without executing snippets or interpreting example values.
Supported HTML uses numbered example headings followed by `pre` or paragraph blocks
and an explicit Constraints list. Unsupported or ambiguous shapes fail explicitly,
including multi-method/stateful APIs, diagrams and missing facts.

Provenance includes requested/returned slugs, separate string internal/frontend
IDs (including special frontend IDs), source GraphQL URL, problem page URL, UTC
fetch timestamp and raw response SHA-256. Full prompt HTML and implementation
snippets are not saved. The unauthenticated fetch refuses premium problems, unknown
slugs, GraphQL errors, redirects, responses above 5 MiB and malformed facts. HTTPS
is required; loopback HTTP is available for local verification with `--leetcode-url`.
Errors print a reason and exit 1; invalid command arguments exit 2.

Sourced facts remain under ignored `.scratch` or an explicit external `--output`
directory. A destination in any Git checkout must ignore each output filename and
the tool's staging paths. Ignoring only the final JSON filename is insufficient.
Git probes have a ten-second timeout and fail closed when checkout or ignore status
cannot be verified, including corrupt repository configuration. Empty staging files
are checked before any source text is written and cleaned up on refusal. The
repository source directories and escaping scratch symlinks are refused. Existing
files are never overwritten: choose a fresh directory for another snapshot. Every
response and target is validated before publication. Each file is published from a
unique staging file with an atomic, exclusive hard link, so concurrent writers
cannot overwrite each other. This requires filesystem hard-link support. A later
filesystem failure may leave an already published prefix of the batch; the command
reports failure and does not promise a multi-file transaction.

Compare the saved signature, constraints and all examples against the exercise
package before recording fetched evidence. Fetching alone does not update
`readiness.json`, learner state or platform acceptance. Human-reported records keep
their existing attribution until an actual fetched comparison is recorded. Hidden
tests and platform verdicts remain unverified.

## Known limits

The runner reports only total duration, not per-case timing, so a slow but correct
solution shows up as a longer run, or a timeout. The hidden LeetCode tests are not
available, so a local pass never proves a platform pass.

A complexity requirement is a test only when it is measured. Answers and total run
time cannot show it: LeetCode 704 asks for `O(log n)`, but a plain scan of 10,000
entries finishes instantly. Package 704 therefore declares a `probe_budget`, so the
runner counts how many different entries of `nums` a solution reads and fails a
correct answer that reads too many (see the [package contract](exercise-package-contract.md)).
Give such a package linear and slicing fixtures that must fail, and keep a fixture
that checks both ends first to show the slack is enough. Say in the statement and
notes what is counted, and record under `not_verified` that a pass is evidence about
reads, not a proof of running time. A requirement with no budget declared is still
only a sentence: say so under `not_verified`.
