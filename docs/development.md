# Development setup

The repository currently provides development tooling, `practice search` and
`practice run` (see the [exercise package contract](exercise-package-contract.md)) and
private attempt history (see [learner history](learner-history.md)) and
preserved reference sources (see [source intake](source-intake.md)).
The tutor contract (a development `CLAUDE.md`, a separate scoped tutor policy and
`practice tutor check`) is described in the [tutor contract](tutor-contract.md).
The first real exercise package (LeetCode 1) is committed under `problems/` and
described in [exercise preparation](exercise-preparation.md). The other practice
commands and packages are still planned.

Install [uv](https://docs.astral.sh/uv/getting-started/installation/), then run
these commands from the repository root in fish, PowerShell, or another shell:

```text
uv sync --locked
uv run --locked ruff check .
uv run --locked ruff format --check .
uv run --locked mypy
uv run --locked pytest
uv run --locked practice tutor check
```

`.python-version` selects Python 3.13.14. uv can acquire that interpreter when
needed. `uv.lock` records the exact resolved development dependencies. Keep it
versioned; ordinary setup and checks use `--locked` to reject a stale lockfile.

The first sync needs package-index access. The clean-checkout end-to-end test
then uses the populated uv cache to install into a separate environment offline.
Keep uv on PATH when running the suite. It checks setup only; these tests do not
establish that the future practice application or tutor behavior works.

The suite also runs real solution files in real child processes, including a
timeout that must leave no stray processes. `tests/fixtures/` holds the Two Sum
runner fixture and its solution variants, and `tests/fixtures/leetcode_two_sum_solutions/`
holds the defective and alternate solutions used against the real package. They are deliberately broken in places,
so Ruff and mypy exclude that directory.

The suite covers configuration contracts, actual successful/failing lint and
strict typing runs, and a clean setup followed by all configured quality gates.
Expected diagnostic failures are captured and asserted rather than printed as
unhandled errors. No mock implementation or external service is used.

`.scratch/` is available for disposable scenario runs and logs. `.venv/`, tool
caches, and `.practice/` are excluded from Git. All learner state lives under
`.practice/`; the setup checks never create it.

Restricted runners may need writable cache and temporary directories. Configure
`UV_CACHE_DIR`, `TEMP`, and `TMP` for that runner rather than changing credentials
or the dependency lock. On systems without hardlink support, uv's documented
`UV_LINK_MODE=copy` setting selects file copying explicitly.

First-party code under `src/`, `tests/` and `tools/` uses strict mypy and Ruff. Keep new
packages inside mypy's `files` setting. Preserved upstream reference files under
`references/` are never edited or linted; they are checked with
`practice sources verify` and run only through separate adapters.

Configuration references: [uv locking](https://docs.astral.sh/uv/concepts/projects/sync/),
[mypy configuration](https://mypy.readthedocs.io/en/stable/config_file.html), and
[Ruff configuration](https://docs.astral.sh/ruff/configuration/).

## Ticket delivery

Complete and verify one testable ticket before opening its PR, ready for review.
Internal implementation phases are not separate approval stops. A PR handles
one ticket; multiple PRs for a ticket require a concrete scope justification.
Drafts are reserved for Joe P's explicit request to share work in progress.

When work is complete, comment on its issue in plain English: describe the
delivered behavior and validation, link all relevant PRs and reference sources,
and state whether merge is pending or complete. Then close the issue as completed.
Keep unfinished work and parents with unmet coverage open. A pending PR merge
alone does not require an otherwise complete implementation issue to stay open.
