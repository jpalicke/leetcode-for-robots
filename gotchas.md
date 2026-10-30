# Gotchas

Rules learned from corrections. Review before starting new work.

- Autonomous pod work continues directly from one completed ticket to the next ready ticket; a PR handoff or merge is not a stop requiring another go-ahead. Keep chat output minimal unless Joe P asks for status, and retain senior review and all quality gates before merging.

- Tickets are organized around deliverables a person can observe, not around internal steps (validate, store, search). Each ticket needs an outcome and a demo.
- Do not guess at missing tickets or hierarchy. Check GitHub for real sub-issues before saying they exist or do not.
- A clean-checkout test must allow the first sync to fill the uv cache. Forcing `--offline` there fails on a cold machine.
- Use `uv run --locked mypy` without `-q`; mypy rejects it.
- Upstream NeetCode Python files are class-only and many annotate with `List[int]` without importing `List`, so they raise `NameError` when imported (704 and 121 do; 20 does not). Never edit the preserved file. The adapter prepends `from typing import List` and appends a top-level wrapper, and the upstream bytes must stay inside it unchanged. Run the upstream file once to see which case you have.
- Treat Joe P's in-progress reports as active ticket reservations; an absent assignee or PR does not make a ticket available.
- Before opening a ticket, list the most recent open issues as well as searching by keyword. A keyword search missed #56, and the duplicate #57 had to be closed as not planned.
- Run the POSIX checks with the Linux uv inside WSL, not the Windows `uv.exe`, and keep it inside the `uv_build` range in `pyproject.toml` (0.11.x). A newer uv warns about that range, and the clean-checkout test fails on the warning.
- Strict mypy checks only the platform it runs on. Write platform code as `if sys.platform == "win32": ... else: ...`, never as an early `return`, and run `mypy --platform win32` and `--platform linux` before trusting either.
