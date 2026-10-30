# Repository development rules

These rules are for people and agents changing this repository. They say nothing
about tutoring. Learner practice sessions start from `tutor/START.md` and follow
`tutor/TUTOR.md`; that policy is kept apart on purpose and is not imported here.
Read `gotchas.md` before starting work and add to it after any correction.

## Commands

Install uv, then run from the repository root:

```text
uv sync --locked
uv run --locked ruff check .
uv run --locked ruff format --check .
uv run --locked mypy
uv run --locked pytest
uv run --locked practice tutor check
```

Use `--locked` everywhere. Do not pass `-q` to mypy. Never edit `uv.lock` by hand.
Python 3.13. The one runtime dependency is `prompt-toolkit` (bounded range), imported
only by `src/practice/menu_tui.py`. Add no other runtime dependency without approval.

## Delivery

- Follow Prompt-Driven Development: one ticket is one deliverable and one PR, opened
  ready for review after the work is verified. No drafts unless asked.
- Work on a branch named for the ticket (`build/...`). Merge to `main` through a PR.
- Never commit with `--no-verify`. If a hook fails, fix the cause.
- Comment on the ticket in plain English when done: what works, how it was verified,
  PR and source links, and whether merge is pending. Then close it.
- One ticket per session. After the merge, stop and tell Joe P to start the next
  ticket in a fresh session.
- Use subagents only for truly parallel, independent work, never merely because a
  ticket exists. The main agent passes the needed file excerpts and line ranges in
  the prompt, so a subagent does not reread `gotchas.md`, docs, or whole modules.
- Docs, issues and scenarios repeat shared text. When a decision changes, grep
  `README.md`, `docs/` and `scenarios.jsonl` for the old wording and run
  `gh issue list --state open --search "<old wording>"`. Read and edit only the
  matching sections; never read a whole doc to audit it.
- Read files with the Read tool and a line range, after a grep finds the lines. Do
  not dump whole files with `cat`, `head` or `Get-Content` chains in the shell.

## Code

- Test first. Write a failing test, watch it fail, then write the least code to pass.
- Every code file starts with two lines that begin with `ABOUTME: `.
- Strict mypy and Ruff cover `src/` and `tests/`. Match the surrounding style.
- Tests use real files and real processes. There is no mock mode, anywhere.
- Test output stays pristine. `filterwarnings = ["error"]` is on; keep it on.
- Name things for what they are, not for when they were written.
- Keep one source of truth. The content classes live in
  `src/practice/classification.py`; read them, never copy them.

## Protected files

- Never edit anything under `references/upstream/` or a license notice. Adapters are
  separate entries (see `docs/source-intake.md`).
- Learner state lives under `.practice/` and is never committed or tracked.
- Keep this file free of tutor behavior. `practice tutor check` enforces it.
