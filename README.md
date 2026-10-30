# leetcode-for-robots

Practice data structures and algorithms locally with a coding-agent tutor.
The learner writes the solution; the tutor offers questions, gradual hints,
realistic tests, explanation feedback, and review suggestions.

**Status: development tooling.** Python setup, quality-gate tests, catalog search, a solution runner, private attempt history and six real exercise packages (LeetCode 1, Two Sum; 217, Contains Duplicate; 242, Valid Anagram; 20, Valid Parentheses; 704, Binary Search; and 121, Best Time to Buy and Sell Stock), which are the six starter problems, are available.
The remaining practice tools and exercise packages are not implemented. Development follows
the reviewed PDD plan, with separate deliverable tickets and verified PRs.

Practice sessions start from `tutor/START.md`, which points the agent at the scoped
policy in `tutor/TUTOR.md`. Development agents read `CLAUDE.md` instead. See the
[tutor contract](docs/tutor-contract.md) for setup and checks for Codex, Claude
Code and optional Cursor.

See [development setup](docs/development.md) to install dependencies and run checks.

Fetch source-attributed problem facts for exercise preparation:

```text
uv run --locked python tools/fetch_problem_facts.py contains-duplicate valid-anagram
```

The JSON files stay under ignored `.scratch/problem-facts/`. They are verification
inputs; compare them with the package before updating readiness evidence. See
[exercise preparation](docs/exercise-preparation.md#fetching-problem-facts).

## Usage

Export public knowledge as deterministic, source-aware JSON for future retrieval:

```text
uv run --locked practice knowledge export leetcode 1
uv run --locked practice knowledge export leetcode 1 --hint-level 2
```

The default exports only the statement summary. Solutions, selected references and
study material (see [study mode](docs/study-mode.md)) need explicit scope; learner data is always excluded. See
[knowledge export](docs/knowledge-export.md) for reveal rules and the JSON contract.

Validate the curriculum map and list the next eligible objectives without learner history:

```text
uv run --locked practice curriculum check
uv run --locked practice curriculum next
uv run --locked practice curriculum next --json
```

See [curriculum and prerequisites](docs/curriculum.md) for the map, custom-file
options and the boundary between placement and exercise readiness.

Search the committed LeetCode catalog snapshot (fetched 2026-10-28) by problem ID,
slug or title fragment:

```text
uv run --locked practice search "two sum"
uv run --locked practice search 1
uv run --locked practice search two-sum
```

Each result shows the learner-visible ID, title, difficulty, a `premium` flag for
paid problems, and the slug. Exit codes: 0 found, 1 nothing matches, 2 usage
error, 3 the catalog file is corrupt or unreadable (the reason goes to stderr).
`--catalog PATH` searches a different catalog file, for example a copy.

Refresh the snapshot with `uv run --locked practice catalog refresh --json`.
See [catalog refresh](docs/catalog-refresh.md) for safe scratch-copy examples,
atomic replacement, change reports and durable coverage mapping flags.

Run a solution file against an exercise package (see the
[exercise package contract](docs/exercise-package-contract.md)):

```text
uv run --locked practice run tests/fixtures/two_sum tests/fixtures/two_sum_solutions/correct_hash_map.py
uv run --locked practice run PACKAGE_DIR SOLUTION.py --timeout 5 --json
```

Exit codes: 0 passed, 1 not passed (failed, error, malformed output, timeout, stub,
unsupported contract or empty suite), 2 usage error, 3 invalid package or suite.
The Two Sum package here is a runner test fixture, not the real exercise.

Keep private attempts and a resumable history under `.practice/` (ignored by Git;
a clean clone never needs it). `--practice-dir PATH` or `$PRACTICE_DIR` moves it:

```text
uv run --locked practice attempt start leetcode 1 --package tests/fixtures/two_sum
uv run --locked practice attempt resume
uv run --locked practice attempt test ATTEMPT_ID --package tests/fixtures/two_sum
uv run --locked practice attempt note-assistance ATTEMPT_ID --kind hint --level 1
uv run --locked practice attempt verdict ATTEMPT_ID --status accepted --source "LeetCode submissions"
uv run --locked practice attempt list
uv run --locked practice attempt finish ATTEMPT_ID
uv run --locked practice progress
uv run --locked practice notes ATTEMPT_ID
```

Every start makes a new blank attempt; earlier code is never touched. Progress and
notes are computed from the journal each time. See
[learner history](docs/learner-history.md) for the design.

## Quick start: LeetCode 1, Two Sum

The first real exercise package is committed under `problems/leetcode-1`, so a fresh
clone needs no `--package` flag:

```text
uv run --locked practice search "two sum"
uv run --locked practice attempt start leetcode 1      # blank typed starter, private copy
uv run --locked practice attempt test ATTEMPT_ID       # stub until you write a body
uv run --locked practice progress leetcode 1           # local result, no platform verdict
uv run --locked practice readiness leetcode 1          # is the package ready, and on what evidence
```

LeetCode 217, Contains Duplicate, is committed the same way under
`problems/leetcode-217`. Its signature and constraints were confirmed by the
project owner from the LeetCode page; the tooling itself could not reach
leetcode.com, and `readiness.json` says so.

LeetCode 242, Valid Anagram, is under `problems/leetcode-242`. Its signature,
constraints and examples were confirmed by the project owner from the LeetCode page,
and `readiness.json` records that they were reported by a person, not fetched.

LeetCode 20, Valid Parentheses, is under `problems/leetcode-20`. Its signature,
constraints and examples were read from LeetCode's GraphQL endpoint when it was
prepared, and `readiness.json` records that they were fetched.

LeetCode 704, Binary Search, is under `problems/leetcode-704`, with facts fetched the
same way. The problem asks for `O(log n)` time, and the package enforces that by
counting how many different entries of `nums` a solution reads: a halving search
reads about 14 of 10,000, and a correct linear scan fails with the count it reached.
The count is evidence about reads, not a proof of running time; the statement, notes
and `readiness.json` say so.

LeetCode 121, Best Time to Buy and Sell Stock, is under `problems/leetcode-121`, also
with fetched facts. A quadratic answer runs out of time on its maximum-length cases
and is reported as a timeout, not a pass.

A blank starter reports `STUB`, never a pass. A local pass is not a LeetCode
acceptance; record that yourself with `attempt verdict`. See
[exercise preparation](docs/exercise-preparation.md) for how packages are made.

## Problem lists

```text
uv run --locked practice lists                 # every list, with ready/blocked/pending counts
uv run --locked practice lists show blind-75   # one list in order, a status on each problem
```

Curated lists such as LeetCode Top Interview 150, LeetCode 75, Blind 75 and NeetCode
150 are committed under `catalog/lists/` and checked against the catalog. A problem
is `[ready]` only when its package passes `practice readiness`; premium problems are
`[blocked]` and everything else is `[pending]`. See [problem lists](docs/lists.md) for
the ten lists, their sources and terms, and how to add one.

## Catalog mapping

Every catalog problem is assigned to exactly one preparation ticket in
`catalog/ticket-plan.json`, grouped by concept and difficulty with premium, SQL and
other non-Python problems kept apart. Check it with
`uv run --locked python tools/plan_catalog.py check`, and see coverage with `report`.
`tools/create_catalog_tickets.py` creates the GitHub issues from the plan (dry run
unless `--apply`). See [catalog mapping](docs/catalog-mapping.md).

## Tutor contract

```text
uv run --locked practice tutor check     # verify the policy, its scoping and ignores
uv run --locked practice tutor start     # safe session settings for a practice session
uv run --locked practice tutor classes   # the content class list the policy carries
```

`tutor check` exits 0 when the contract holds and 3 when it does not, printing
every problem to stderr. `tutor start` prints the mode, timing and the active
attempt but never code, notes or assistance text.

## Reference sources

Published reference code is preserved byte for byte, with its license notice and
a provenance manifest, under `references/`:

```text
uv run --locked practice sources verify
uv run --locked practice sources show neetcode-leetcode-0001-two-sum-python
uv run --locked practice sources add ID --repository URL --revision SHA --path PATH ...
```

```text
uv run --locked practice sources validate ID --package problems/leetcode-1
```

`sources validate` runs a preserved reference file against a package and records the
result, bound to the file's SHA-256 and the suite hash. Platform acceptance is never
touched by it. Intake itself never runs the code and claims nothing about correctness. See
[source intake](docs/source-intake.md).

## Planning documents

- [Requirements and agreed decisions](docs/requirements.md)
- [Specification draft](docs/specification.md)
- [Published reference research and source policy](docs/reference-sources.md)
- [Source intake and provenance manifests](docs/source-intake.md)
- [Development backlog proposal](docs/development-backlog.md)
- [Ticket-based implementation plan](docs/implementation-plan.md)
- [First-release acceptance evidence](docs/first-release-acceptance.md)

## Planned scope

- Python first, with Codex and Claude Code support and an editor-independent workflow.
  Cursor remains an optional choice.
- Both a tutor-chat menu and a terminal menu. Terminal tutoring actions prepare
  requests to paste into an existing agent chat.
- Full LeetCode catalog coverage, with preparation tracked as development tasks
  in GitHub issues. Six easy exercises form the first validated batch.
- Study and practice modes; study is an explicit choice from the menu, with cited
  units described in [study mode](docs/study-mode.md). Timed practice is strictly
  optional.
- Local completion, explanation grading, and LeetCode acceptance tracked separately.
- Personal attempts, progress, notes, and generated requests excluded from Git by default.
- Locally stored reference code with citations, preserved source notices, and
  independent validation; published implementations are preferred.
- A structure ready for a follow-up RAG experiment.

The project is intended for noncommercial use. Selected third-party reference
material retains its own license and attribution requirements.

Future refinements include C++, Rust, Go, CodeFights, and HackerRank.
