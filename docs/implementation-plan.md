# PDD implementation plan

Prepared for Joe P on 2026-10-28. Status: ticket structure reconciled; tooling complete; implementation proceeds ticket by ticket.
Requirements and specification remain authoritative for approved behavior.
Joe P approved these defaults after removing the five-file limit for this project.

## Release boundary

The first usable release (milestone `v0.1`) has a searchable full-catalog snapshot,
six verified Python exercises, both menus, private progress, gradual tutoring,
explanation assessments, spaced reviews, recommendations, and a filtered knowledge
export. The remaining catalog is explicitly tracked preparation work outside the
release; first release does not require every catalog entry to be runnable.

First vertical slice (label `slice-1`): practice Two Sum end to end by searching,
starting an attempt, running tests and seeing progress. It needs the search
deliverable, the runner, the attempt lifecycle and the Two Sum package.

The [catalog parent](https://github.com/jpalicke/leetcode-for-robots/issues/1)
links all workstreams. [Issue #3](https://github.com/jpalicke/leetcode-for-robots/issues/3)
tracks this review. Tickets define delivery boundaries; phases are internal steps.

## Implementation decisions

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

## Ticket and PR contract

A ticket describes one complete, testable deliverable. Tooling and the tutor
contract are separate tickets. Internal design, TDD, implementation, and review
steps do not require separate tickets or repeated approval handoffs.

- Each PR addresses exactly one implementation ticket. Normally one PR resolves
  it; two or three are exceptions justified by the deliverable itself.
- No fixed file-count limit applies. Split unrelated outcomes, not arbitrary
  numbers of files or problems.
- Implement and verify the authorized ticket before opening its PR, ready for
  review. Use drafts only when Joe P explicitly requests sharing work in progress.
- Tracking parents organize related work; they are not implementation tickets
  requiring one enormous PR. Use actual GitHub sub-issue relationships.
- Once a ticket is complete, first post a plain-English completion comment:
  describe what changed, what now works, and the verification performed; link
  all relevant PRs and reference sources; distinguish implemented, reviewed,
  and merged status. Then close the issue as completed. A pending merge does
  not keep a completed implementation ticket open.
- Never close unfinished or blocked work as completed. A tracking parent closes
  only when its defined scope and coverage criteria are satisfied.
- Prefer Sol or Sonnet; Luna or Haiku only for suitable lightweight work. Delegate
  through sequential subagents, one at a time, Sonnet by default and Haiku for light work.
  Do not raise reasoning effort or use Astra High without explicit approval.

## Deliverables and dependencies

The backlog file is the reconciled issue index. Names below define scope and
map to the linked GitHub tickets there. Every row is an implementation
outcome unless explicitly marked as a tracking parent.

| Deliverable | Definition of done | Prerequisites |
| --- | --- | --- |
| Python development tooling | Locked environment; strict typing; lint/format; real setup tests; documented clean setup | Approved planning baseline |
| Shared tutor contract | Development CLAUDE.md plus a scoped tutor-policy file used only by practice sessions, optional Cursor setup, policy checks and live agent evidence | Tooling |
| Search the catalog from the terminal | Commit and validate the real dated snapshot, `practice search` by ID/title/slug, reject corrupt input | Tooling |
| Refresh the catalog without losing work | Fetch, validate, atomic swap, report added/changed/removed, keep last good snapshot on failure | Catalog search |
| Catalog preparation coverage tracking | A `tools/` mapping script groups entries into class tickets of at most 100 (GitHub sub-issue cap), creates them in resumable rate-limited batches, treats premium entries as one blocked class, and reports coverage without omissions | Catalog |
| Published-reference intake | Preserve a selected real source file/notices unchanged with revision/hash, citation, terms and separate adapter location | Tooling; tutor content classifications |
| Ordinary Python exercise runner | Execute primitive/list/string contracts; accept valid alternate outputs; fail honestly on errors, stubs, empty suites and timeouts; return code/suite hashes | Tooling; documented package contract |
| Attempt lifecycle and private history | Create blank attempts, preserve prior work, resume interruptions, save real events, attach evidence to exact versions, derive notes | Catalog; runner |
| Two Sum exercise package | Complete statement/signature/starter, preserved or original reference, hints, tests, independent checks and readiness evidence | Reference intake; runner |
| Each of the other five starter packages | Same per-problem contract, one problem per implementation ticket | First package standard; relevant source/runner support |
| Explanation assessments | Store initial/revised evidence; 4/4/2 plus separate space bonus; ungraded differs from zero; slower correct explanations can earn full credit | Private history; tutor contract |
| Spaced reviews | Blank preserved re-solving; 1/3/7/14/30-day suggestions; assistance-aware adjustment; skip/reschedule without penalty | Attempt lifecycle |
| Curriculum recommendations | Deterministic due-review/prerequisite/curriculum selection, override support, no visible technique leakage | Catalog; history; assessments; reviews |
| Shared chat and terminal navigation | Browse/select/resume/test/progress actions use the same state; real terminal and live chat acceptance evidence | Catalog; attempts; runner; tutor contract; related actions |
| Paste-ready tutor requests | Correct problem/attempt/mode/action context; permitted reveal only; local ignored output; no automatic send/launch or false assistance event | Attempts; tutor contract; navigation |
| Filtered knowledge export | Stable IDs/provenance, deterministic output, pre-context reveal filtering, no default solutions or learner data | Reference metadata; tutor classifications |
| Full catalog (tracking parent) | Complete snapshot mapping and prepared in-scope exercises; unfinished or blocked preparation keeps this parent open | Preparation coverage and problem/class children |
| Six starter exercises (tracking parent) | All six individual exercise children meet readiness criteria | Six problem tickets |
| Curriculum and prerequisite map | Ordered concepts and prerequisites for the starters, validated, no technique labels in practice mode | Catalog |
| Study-mode lessons | Cited, classified teaching units for the starter concepts, opted into from both menus ([study mode](study-mode.md)) | Source intake; export; tutor contract |
| Optional timed practice | Per-attempt opt-in timing that resets and never affects explanation scores | Navigation; history |
| First-release acceptance | Clean-clone run of the spec scenarios with recorded evidence | Other v0.1 tickets |
| Future refinements (tracking parent) | Separate discovery tickets for RAG, C++, Rust, Go, CodeFights and HackerRank; each defines its own implementation work | First-release baseline as relevant |

Node-based, mutation, stateful and interactive execution contracts get separate
adapter tickets when required by problem classes. Do not imply these are part
of the first ordinary-Python runner. Keep non-Python and inaccessible problems
visible in coverage without claiming they can run locally.

## Catalog issue hierarchy

Use full-catalog parent #1, with coherent problem/class tracking children and
individually implementable leaves. The six-starter parent #8 contains six actual
problem sub-issues. Other class groups are based on a validated inventory and
execution needs, not an arbitrary batch size or guessed problem metadata.

Every catalog entry must map exactly once to a preparation leaf or a clearly
scoped class preparation ticket. Nested tracking parents may aggregate those
leaves. Infra dependencies are linked, not counted as prepared problems.
Creation and hierarchy mapping must be resumable and duplicate-safe. The full
4,096-entry discovery snapshot is a target inventory, not a claim that all
preparation children already exist. Coverage tracking remains open until the
complete mapping is verified. Refresh reconciles additions without losing work.

## Verification and delivery order

Use TDD for code: run a failing scenario, implement minimally, then refactor with
checks green. Use real files/processes/APIs, no mock mode. Each deliverable needs
unit, integration, and end-to-end coverage appropriate to its behavior. Run
strict mypy, configured lint and formatting checks, the full test suite, inspect
logs, and simulate actual usage before reporting implementation complete.

Preserved upstream code is not reformatted or annotated. Strictly check local
adapters and independently validate references. A reference source's execution
is validated by the runner/problem package, not a prerequisite cycle in source
intake. Live agent behavior needs actual Codex and Claude Code sessions; static
text checks cannot prove compliance. Record unavailable checks as pending.

Start with tooling, then tutor contract and catalog. Build source intake and the
ordinary runner against a documented package contract. Validate Two Sum and the
attempt lifecycle, then prepare the remaining starter packages. Add assessments,
reviews, recommendations, navigation and handoff according to their dependencies.
The knowledge export can proceed once its source/classification contracts exist;
it does not need to wait for every progress feature merely to exclude learner data.

Cross-cutting acceptance belongs to the ticket that delivers the behavior:
clean clone, timer reset, blank reviews, accurate slow-solution grading, alternate
outputs, privacy and reveal boundaries. A final release checklist checks the
combined workflow without becoming a miscellaneous multi-ticket implementation PR.

Navigation depends on the catalog, runner, history and tutor contract; reviews and
recommendations wire in their own menu actions. Preparation pipeline documentation
is part of the Two Sum package ticket.
