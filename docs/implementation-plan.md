# PDD implementation plan

Prepared for Joe P on 2026-10-28. Status: approved baseline; phase 1 authorized.
Requirements and specification remain authoritative for approved behavior.
Joe P approved these defaults after removing the five-file limit for this project.

## Release boundary

The first usable release has a searchable full-catalog snapshot, six verified
Python exercises, both menus, private progress, gradual tutoring, and a filtered
knowledge export. The remaining catalog is explicitly tracked preparation work;
first release does not require every catalog entry to be runnable.

The [catalog parent](https://github.com/jpalicke/leetcode-for-robots/issues/1)
links all workstreams. [Issue #3](https://github.com/jpalicke/leetcode-for-robots/issues/3)
tracks this review. Subsequent phases retain their individual approval gates.

## Proposed implementation decisions

1. Use a Python package with a `practice` terminal entry point. Use uv, pytest,
   Ruff, and strict mypy. Pin the Python version and dependency versions during
   tooling setup after checking compatibility. Keep runtime dependencies minimal.
2. Use JSON metadata and Markdown learning content. Store shared content under
   `catalog/`, `problems/`, and `knowledge/`; preserved upstream files under
   `references/`. Put all learner files under ignored `.practice/`.
3. Use an append-only local event journal as the authority for progress. Derive
   menus, notes, scores, review dates, and summaries from events; do not maintain
   an independently editable progress database. Attempts are separate code files.
   Write complete journal records, serialize local writers, and report malformed
   records without silently discarding history. No sync service in this release.
4. Identify a problem by platform and platform ID. Attempts have separate IDs,
   language, code hash, and mode. Test results also identify suite version/hash.
   Edited code has no current pass until retested; previous evidence is retained.
5. Catalog membership and language readiness are separate. Readiness requires a
   verified callable contract, starter, reference provenance, independent checks,
   runnable suite, and execution evidence. Missing material stays pending/blocked.
6. Treat hint levels as ordered assistance events. A generic hint request permits
   one next step; a full reveal requires an explicit request. Reset permissions
   for each attempt. Study mode permits concept instruction, but permission to
   edit learner code remains separate. Never infer editing permission from reveal.
7. Offer one check-in after two materially similar failures or explicit confusion.
   The tutor interprets similarity using visible evidence, without a background
   monitor. Silence and elapsed time never trigger a check-in. After a decline,
   wait for meaningful new evidence or a request before offering again.
8. Start the first suggested review one day after completion. After an independent
   successful review, advance through 3, 7, 14, then 30 days; retain 30 thereafter.
   With substantial algorithm help, full reveal, or an unresolved misconception,
   suggest a one-day review. Syntax clarification alone does not reset the gap.
   Anchor intervals to the actual review date; skipping does not lower a score.
   Treat this as a transparent scheduling heuristic, not a mastery claim.
9. Recommend due reviews first, then prerequisite gaps, then the next curriculum
   objective. Break ties deterministically. Allow overrides and avoid showing
   technique labels in practice recommendations. Record the reason internally.
10. Run learner code in a child process with a time limit and fresh inputs.
    A timeout, import error, malformed output, missing suite, or stub is a failed
    or incomplete run. This process boundary limits runaway execution; it does
    not provide a security sandbox for arbitrary downloaded code.
11. Terminal tutoring actions write a local paste-ready request. Include only
    selected allowed context and paths, never a broad reference-directory request.
    Generating a request is not recorded as receiving a hint. Tutor instructions
    record actual assistance events when delivered.
12. Default knowledge export contains approved problem context only. Hints require
    a permitted level; references/solutions require explicit reveal. Filter before
    reading content into the request/export. Repository files remain inspectable:
    this reduces accidental spoilers rather than enforcing secrecy from learners.

## Explanation score anchors

Score the explanation of the submitted code, independently of local completion,
optimization opportunities, hints, and elapsed time. A skipped explanation is
ungraded. Record initial and revised explanations distinctly.

| Component | Proposed whole-number anchors |
| --- | --- |
| Approach /4 | 0 absent/incorrect; 1 isolated accurate fragments; 2 main idea with material gaps; 3 accurate flow with a minor omission; 4 clear and accurate account of key operations |
| Why it works /4 | 0 absent/incorrect; 1 unsupported assertion; 2 partly sound reasoning with a material gap; 3 sound reasoning with a minor omission; 4 convincing reasoning covering relevant boundaries |
| Time /2 | 0 incorrect/absent; 1 correct order with incomplete reasoning; 2 defines input size and accounts for dominant work correctly |
| Space bonus +1 | 0 omitted/incorrect; 1 correctly identifies significant auxiliary storage and its growth |

Do not require formal proofs or artificial verbosity. A simple problem can earn
full reasoning credit in a short explanation. Report core /10 and bonus separately.

## Development and verification contract

- This project has no per-phase file-count limit. Scope phases around coherent outcomes.
  Stop after its checks and wait for Joe P's approval before the next phase.
- The table below defines phase boundaries and acceptance contracts. Before each
  phase, identify the expected paths and acceptance evidence. Split work when it
  improves reviewability; do not split merely to satisfy an arbitrary file count.
- For code, write and run the failing scenario first, implement minimally, then
  run relevant checks. Use real files, child processes, and APIs; no mock mode.
- Cover unit, integration, and end-to-end behavior across the product. E2E tests
  launch the actual command in a temporary workspace and inspect real artifacts.
- Before reporting an implementation phase complete, run strict mypy, all
  configured Ruff checks/format checks, and the complete configured test suite.
  Inspect logs and exercise its real user flow. Capture expected errors in tests.
- Preserved upstream code is not reformatted, annotated, or made to satisfy
  first-party typing rules by modification. Type-check adapters strictly and
  execute upstream references through their independent validation contracts.
- Evaluate tutor behavior in actual Codex and Claude Code sessions. Automated
  file/process tests cannot establish instruction following. If either runtime
  is unavailable, leave that compatibility check pending rather than claim a pass.
- Use individual branches, normal hooks, and review. Never bypass hooks.

## Phases

Each row is a gated increment, not permission to execute the whole table at once.
Related issues express workstreams; they can span several phases.

| Phase | Scope | First failing scenario and exit evidence | Issue |
| --- | --- | --- | --- |
| 1 | Tooling only: `pyproject.toml`, `uv.lock`, and three smoke tests under unit/integration/e2e | Configure and run a failing development-setup check before resolving dependencies; then verify locked environment, strict checker, lint/format, and three real setup smoke tests. These test setup only, not product features. | #4 |
| 2 | `AGENTS.md`, `CLAUDE.md`, `.gitignore`, and policy/private-state contract tests | A missing policy clause or unignored learner path fails; verify hint/edit/timing/privacy rules and instruction loading in supported live agents. Establish the ignore boundary before creating attempts. Pick the requested project nicknames when creating AGENTS.md. | #4 |
| 3 | Catalog schema/validator and tests | Duplicate/invalid identities and malformed snapshots fail; valid real catalog records parse without treating membership as readiness. | #5 |
| 4 | Catalog acquisition/search command and real process tests | Search a stored real snapshot; refresh failure preserves it; validate a live acquisition separately. Store fetch evidence and age. | #5 |
| 5 | Preparation batch generator, manifest, coverage report, and tests | Every entry in the named snapshot maps exactly once to a task; duplicates/omissions fail. Create bounded GitHub batch issues after validating the generated inventory, using resumable IDs to avoid duplicates. | #1, #5 |
| 6 | Provenance/source intake schema, validation, and tests | Missing citation/revision/notice evidence blocks imported references; an original reference can use explicit original provenance. Verify preserved file hashes. | #6 |
| 7 | Execution contract and primitive-input runner with unit/integration/e2e coverage | Real incomplete, wrong, valid alternate, and runaway attempts produce distinct honest outcomes. Run actual child processes. | #7 |
| 8 | Attempt creation and journal persistence with tests | Resume an interrupted session; preserve prior code; code/suite changes invalidate current pass; incomplete writes and concurrent writers cannot silently lose history. | #10 |
| 9 | First complete Two Sum package | A blank starter fails, a known defect fails, valid alternative algorithms pass, and the preserved reference passes independent small-input checks. Require provenance and readiness evidence. | #8 |
| 10 | Remaining five starters, one complete problem at a time | Apply the same independent checks and readiness checklist to each problem. Each increment has its own verification/approval gate. | #8 |
| 11 | Search/select/resume/test terminal menu and real interaction tests | A clean clone initializes private state; a real menu session selects and tests a ready exercise. Pending exercises never appear runnable. | #9 |
| 12 | Shared chat-menu rendering, filtered tutor-request builder, contextual actions, and tests | Both menus reflect the same active state. Hint requests omit references/previous code; generated requests do not log delivered assistance. Confirm no agent launches/messages. | #9 |
| 13 | Explanation assessments/derived notes with tests | Ungraded differs from zero; core and bonus separate; evidence attaches to attempt/code version and feedback revision. | #10 |
| 14 | Review scheduling/recommendations with tests | Independently successful and assisted reviews produce agreed dates; skipped dates have no penalty; recommendation labels reveal no technique. | #10 |
| 15 | Knowledge chunk metadata/export and tests | Default export excludes solutions and all learner state; explicit reveal includes only authorized problem/language content with provenance. | #11 |
| 16 | Clean-clone documentation and acceptance evidence | Exercise both menus and live tutors; blank review, optional timer reset, alternate solution, slow-solution grading, private state, and export scenarios pass. | #3, #4, #9–#11 |

After the first release, preparation batches continue under #1. Implement
specialized node/stateful/mutation adapters through separately gated increments
under #7 before marking affected problems ready. Track unavailable/premium and
non-Python formats explicitly. The retrieval experiment and language/platform
extensions remain separate follow-ups in #12.

## Review findings and tradeoff

The existing specification/backlog incorrectly said issues were not posted;
those statements should now point to #1 and #3–#12. The confirmed grading weights
remain 4/4/2 plus a separate space bonus; time is not the dominant component.

A perfectionist would want complete problem schemas, every test-adapter contract,
and calibrated live-tutor transcripts before implementation. A pragmatist can
accept the bounded decisions here, validate them with Two Sum end to end, and
refine specialized contracts before their own phases. The proposed choice is the
latter, while preserving explicit review gates and honest readiness reporting.

Joe P approved the defaults, score anchors, and phased approach on 2026-10-28.
That approval authorizes phase 1 only; subsequent phases retain their own gate.
