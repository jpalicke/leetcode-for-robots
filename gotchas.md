# Gotchas

Rules learned from corrections. Review before starting new work.

- Tickets are organized around deliverables a person can observe, not around internal steps (validate, store, search). Each ticket needs an outcome and a demo.
- Do not guess at missing tickets or hierarchy. Check GitHub for real sub-issues before saying they exist or do not.
- Planning docs and issue bodies repeat shared text. When a decision changes, search every doc and open issue for the old wording.
- A clean-checkout test must allow the first sync to fill the uv cache. Forcing `--offline` there fails on a cold machine.
- Use `uv run --locked mypy` without `-q`; mypy rejects it.
- Upstream NeetCode Python files are class-only and many annotate with `List[int]` without importing `List`, so they raise `NameError` when imported (704 and 121 do; 20 does not). Never edit the preserved file. The adapter prepends `from typing import List` and appends a top-level wrapper, and the upstream bytes must stay inside it unchanged. Run the upstream file once to see which case you have.
- Before opening a ticket, list the most recent open issues as well as searching by keyword. A keyword search missed #56, and the duplicate #57 had to be closed as not planned.
