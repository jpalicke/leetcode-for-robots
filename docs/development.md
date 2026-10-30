# Development setup

The repository currently provides development tooling, `practice search` and
`practice run` (see the [exercise package contract](exercise-package-contract.md)) and
private attempt history (see [learner history](learner-history.md)) and
preserved reference sources (see [source intake](source-intake.md)).
Paste-ready requests for an existing tutor chat are described in
[tutor requests](tutor-requests.md).
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
uv run --locked practice curriculum check
uv run --locked practice curriculum next
uv run --locked practice catalog refresh --help
```

`.python-version` selects Python 3.13.14. uv can acquire that interpreter when
needed. `uv.lock` records the exact resolved development dependencies. Keep it
versioned; ordinary setup and checks use `--locked` to reject a stale lockfile.

The one runtime dependency is `prompt-toolkit`, bounded to `>=3.0.52,<4`. It gives
`practice tui` arrow-key selection that also works with number keys. It is pure
Python, runs on Windows and POSIX terminals, and ships a pipe input that the tests
use to drive the real menu without any mock. Only `src/practice/menu_tui.py`
imports it, and a test enforces that, so the shared menu, the numbered menu and
every other command work without it. Add no further runtime dependency without
approval.

The first sync needs package-index access. The clean-checkout end-to-end test
allows its locked sync to populate the uv cache while installing a separate
environment; subsequent verification commands use that environment offline.
Keep uv on PATH when running the suite. It checks setup only; these tests do not
establish that the future practice application or tutor behavior works.

On Windows, the suite uses compact, unique `t0`, `t1`, ... fixture directories
through the public `tmp_path_factory.mktemp` API. Pytest still retains session
folders under its usual base directory, but the directory name no longer records
the test name; failure tracebacks show the actual path. The independent checkout
uses a separate `lc-...` directory directly under Python's OS temporary directory
and removes it after verification. Ordinary Windows user temporary paths work
without manually selecting a short drive-root directory or enabling long paths.

Preserved reference names remain unchanged. A preflight rejects Windows fixture
paths that would exceed the portable 259 UTF-16 code-unit file-path budget,
including a 20-code-unit allowance for fixture subfolders. Non-BMP characters
such as emoji consume two UTF-16 code units each. If a custom temporary root is too
long, set `TEMP` and `TMP` to a shorter writable directory before starting pytest.
`--basetemp` controls pytest fixture storage only; it does not change the clean
checkout's OS temporary root. No drive mapping or registry change is required.
See [pytest temporary directories](https://docs.pytest.org/en/stable/how-to/tmp_path.html)
and [Python temporary-directory selection](https://docs.python.org/3/library/tempfile.html#tempfile.gettempdir).

Each verification command has a deadline: 600 seconds for the nested unit and
integration suite, 120 seconds for other checks. On timeout the harness terminates
the command's process tree and reports the command, deadline, captured stdout and
stderr, and any cleanup failure. Cleanup gets at most 10 seconds for Windows
`taskkill` and 5 seconds to reap the launcher. File-backed capture avoids waiting
for descendant processes to close inherited output pipes. The learner solution
runner is separate. See [Python subprocess timeouts](https://docs.python.org/3/library/subprocess.html#subprocess.Popen.communicate).

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

The [curriculum map](curriculum.md) is committed under `curriculum/`. Its tests
validate real catalog placements, malformed prerequisite graphs, stable objective
order and learner-safe CLI output using real files and subprocesses.

## Hosted quality gates

`.github/workflows/quality.yml` runs on every pull request, pushes to `main`, and
manual dispatch. The stable check names are `Quality (ubuntu-24.04)` and
`Quality (windows-2022)`. Both install uv 0.11.26, use the Python version in
`.python-version`, run locked sync, Ruff lint/format, strict mypy for the native,
Windows and Linux targets, tutor/curriculum contracts, preserved-source integrity,
and the complete unit/integration/end-to-end suite. Existing platform skips remain
visible; the workflow adds none. The independent-checkout gate runs inside pytest.

Jobs have a 45-minute limit and the test step has a 35-minute limit, in addition
to the existing subprocess deadlines. Matrix failures do not cancel the other OS.
A newer run cancels an older run for the same pull request or branch. Ordinary
runner temporary directories are used without shortening `TEMP` or skipping tests.

Actions are pinned to reviewed immutable revisions: checkout v7.0.1, setup-uv
v10.3.3 and upload-artifact v7.0.2. These use Node 24 on GitHub-hosted runners.
Workflow permissions are `contents: read`; checkout does not persist credentials.
There are no repository secrets or model calls. The uv cache is separated by OS,
architecture, interpreter file and lockfile; only trusted `main` pushes save it.
The workflow never caches learner directories or uploads the checkout/scratch tree.

Each OS retains only `ci-results/tests.xml` for seven days, including failures;
the run's native step logs hold setup/type/lint diagnostics. The artifact contains
test diagnostics from synthetic fixtures, never real learner history. Local JUnit
output under `ci-results/` is ignored by Git.

Maintainers should require both stable check names before merging. Adding a
workflow does not enable branch protection automatically; do not report
enforcement until repository settings confirm it.

Official references, checked 2026-10-30:
[checkout](https://github.com/actions/checkout/tree/v7.0.1),
[setup-uv](https://github.com/astral-sh/setup-uv/tree/v10.3.3),
[upload-artifact](https://github.com/actions/upload-artifact/tree/v7.0.2),
[uv integration](https://docs.astral.sh/uv/guides/integration/github/).
