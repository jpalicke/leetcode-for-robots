# leetcode-for-robots

Practice data structures and algorithms locally with a coding-agent tutor.
The learner writes the solution; the tutor offers questions, gradual hints,
realistic tests, explanation feedback, and review suggestions.

**Status: development tooling.** Python setup, quality-gate tests, catalog search, a solution runner and private attempt history are available.
The remaining practice tools and exercise packages are not implemented. Development follows
the reviewed PDD plan, with separate deliverable tickets and verified PRs.

See [development setup](docs/development.md) to install dependencies and run checks.

## Usage

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

## Planning documents

- [Requirements and agreed decisions](docs/requirements.md)
- [Specification draft](docs/specification.md)
- [Published reference research and source policy](docs/reference-sources.md)
- [Development backlog proposal](docs/development-backlog.md)
- [Ticket-based implementation plan](docs/implementation-plan.md)

## Planned scope

- Python first, with Codex and Claude Code support and an editor-independent workflow.
  Cursor remains an optional choice.
- Both a tutor-chat menu and a terminal menu. Terminal tutoring actions prepare
  requests to paste into an existing agent chat.
- Full LeetCode catalog coverage, with preparation tracked as development tasks
  in GitHub issues. Six easy exercises form the first validated batch.
- Study and practice modes; timed practice is strictly optional.
- Local completion, explanation grading, and LeetCode acceptance tracked separately.
- Personal attempts, progress, notes, and generated requests excluded from Git by default.
- Locally stored reference code with citations, preserved source notices, and
  independent validation; published implementations are preferred.
- A structure ready for a follow-up RAG experiment.

The project is intended for noncommercial use. Selected third-party reference
material retains its own license and attribution requirements.

Future refinements include C++, Rust, Go, CodeFights, and HackerRank.
