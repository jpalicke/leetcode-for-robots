# Development setup

The repository currently provides development tooling. Practice commands,
exercise packages, and tutor instruction files are still planned.

Install [uv](https://docs.astral.sh/uv/getting-started/installation/), then run
these commands from the repository root in fish, PowerShell, or another shell:

```text
uv sync --locked
uv run --locked ruff check .
uv run --locked ruff format --check .
uv run --locked mypy
uv run --locked pytest
```

`.python-version` selects Python 3.13.14. uv can acquire that interpreter when
needed. `uv.lock` records the exact resolved development dependencies. Keep it
versioned; ordinary setup and checks use `--locked` to reject a stale lockfile.

The first sync needs package-index access. The clean-checkout end-to-end test
then uses the populated uv cache to install into a separate environment offline.
Keep uv on PATH when running the suite. It checks setup only; these tests do not
establish that the future practice application or tutor behavior works.

The suite covers configuration contracts, actual successful/failing lint and
strict typing runs, and a clean setup followed by all configured quality gates.
Expected diagnostic failures are captured and asserted rather than printed as
unhandled errors. No mock implementation or external service is used.

`.scratch/` is available for disposable scenario runs and logs. `.venv/`, tool
caches, and `.practice/` are excluded from Git. All learner state will live under
`.practice/`; no learner history is initialized by these setup checks.

Restricted runners may need writable cache and temporary directories. Configure
`UV_CACHE_DIR`, `TEMP`, and `TMP` for that runner rather than changing credentials
or the dependency lock. On systems without hardlink support, uv's documented
`UV_LINK_MODE=copy` setting selects file copying explicitly.

First-party code uses strict mypy and Ruff. When application code is introduced,
include its package in mypy's `files` setting. Preserved upstream reference files
will be checked through separate adapters without editing their contents.

Configuration references: [uv locking](https://docs.astral.sh/uv/concepts/projects/sync/),
[mypy configuration](https://mypy.readthedocs.io/en/stable/config_file.html), and
[Ruff configuration](https://docs.astral.sh/ruff/configuration/).
