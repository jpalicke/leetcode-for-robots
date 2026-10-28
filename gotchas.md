# Gotchas

Rules learned from corrections. Review before starting new work.

- Tickets are organized around deliverables a person can observe, not around internal steps (validate, store, search). Each ticket needs an outcome and a demo.
- Do not guess at missing tickets or hierarchy. Check GitHub for real sub-issues before saying they exist or do not.
- Planning docs and issue bodies repeat shared text. When a decision changes, search every doc and open issue for the old wording.
- A clean-checkout test must allow the first sync to fill the uv cache. Forcing `--offline` there fails on a cold machine.
- Use `uv run --locked mypy` without `-q`; mypy rejects it.
