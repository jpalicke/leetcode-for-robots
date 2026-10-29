# DSA practice repository: specification draft

Status: approved planning baseline, reconciled on 2026-10-28; tooling complete.
Date: 2026-10-28. Requirements source: requirements.md.

## 1. Product intent

Help Joe P rebuild DSA fundamentals and prepare for technical interviews by
solving problems locally with an AI tutor. Joe P writes the solutions. The tutor
supports understanding, tests the work, records learning evidence, and suggests
what to practice next.

Confirmed requirements are recorded in requirements.md. Sections explicitly
marked Proposal retain their discovery labels. The implementation plan records
the approved defaults and phase approval boundaries.

## 2. Confirmed product boundaries

- Python first; C++, Rust, and Go are future language refinements.
- Full LeetCode catalog coverage, with question preparation tracked as development tasks in GitHub issues.
- Codex and Claude Code supported; Cursor remains optional. No editor dependency.
- Local coding first; LeetCode acceptance tracked separately from local completion.
- Practice mode by default; study mode available; timing strictly opt-in per session.
- Gradual assistance, explicit requests for full solutions, and edits as a last resort.
- Automatic session notes, adaptive curriculum, and spaced review.
- A core explanation score out of 10, emphasizing the approach and correctness reasoning,
  plus up to one separate bonus point for space complexity. Optimization coaching
  is a separate discussion.
- RAG is a fast follow. CodeFights and HackerRank are platform stretch goals.

## 3. First-release scope

Confirmed outline: six prepared easy Python problems form the first validated batch;
preparation of the remaining full catalog is planned development work tracked in GitHub issues. The workflow
and implementation details below remain proposals for specification review.

Proposal: the first release is a file-based repository used through ordinary
conversation with a coding agent. A small local Python tool handles repeatable
operations such as catalog lookup, workspace creation, tests, and progress records.
Joe P should not need to memorize commands to practice.

Include:

1. A dated, searchable catalog snapshot with source and refresh information.
2. Six fully prepared easy Python exercises to verify the complete workflow:
   Two Sum, Contains Duplicate, Valid Anagram, Valid Parentheses, Binary Search,
   and Best Time to Buy and Sell Stock. These are a starting pack, not a catalog limit.
3. A documented preparation pipeline and GitHub development backlog covering every catalog entry, with per-problem readiness and tracked blockers.
4. A scoped tutor policy for practice sessions and a separate development CLAUDE.md,
   with thin instruction entry points for supported agents.
5. Realistic local tests, preserved attempts, automatic progress notes, and reviews.
6. A curriculum outline and recommendation policy, without exposing technique
   labels during ordinary practice.
7. Structured knowledge files and a deterministic export for later RAG evaluation.

A listed problem can be cataloged, awaiting preparation, or ready for local
practice. It must not appear runnable until its signature, adapter, and tests
have been prepared and validated. Python-incompatible tasks, including SQL-only
or shell-only problems, can remain catalog entries without claiming Python support.
Specialized problems need their own verified local adapter before becoming ready.

## 4. Learner workflow

Confirmed interface: provide both a numbered tutor-chat menu and an interactive
terminal menu. Both use the same active attempt and progress records. Free-text
requests remain available in chat.

The main menu offers resume, recommend, browse/select, reviews, study, progress
and notes, and explicitly optional timed practice. A contextual problem menu
includes run tests, request a hint, explain the solution, and return to the main
menu. Showing a menu must not reveal techniques or solutions.

Terminal actions such as browsing and running local tests can execute directly.
Confirmed handoff: for hints, study, explanation grading, and other conversational
actions, prepare a request the learner can paste into an existing coding-agent
chat. The request identifies the active problem/attempt, relevant local paths,
selected action, mode, and permitted reveal level. Include only context allowed
by that mode and reveal level; a request must not contain a hidden answer.
The terminal menu does not launch an agent or send a message automatically.
Preparing a request is not a delivered hint; the agent records assistance when
it actually provides it. Runtime details and request formatting belong in the plan.

Proposal:

1. Begin a session. Default to untimed practice; read the learner's current
   progress without exposing previous solution code in the conversation.
2. Ask for a recommendation or choose a problem by platform ID, title, or slug.
3. Present the problem, constraints, examples, and a blank typed Python starter.
   Do not display intended techniques, reference code, or previous attempts.
4. Joe P writes code. The agent can run tests and discuss observable results.
5. If struggle is apparent, offer a gentle check-in without giving a hint first.
6. When the required local suite passes, record local completion and invite an
   explanation. Joe P can defer the explanation without losing completion.
7. Grade the explanation, discuss possible optimizations gradually, and save notes.
8. Joe P may submit to LeetCode and share the result. Record platform acceptance
   independently and link it to the submitted attempt when that evidence is available.
9. Save review needs and offer a next step. No automatic reminders are created.

Starting a review creates another blank attempt. Existing attempts are preserved.
A later failed attempt does not erase the evidence that an earlier attempt passed.
Results attach to a specific attempt and code version, so modifying code does not
silently keep a stale passing result attached to the edited version.

## 5. Study, practice, hints, and editing

Confirmed: study mode may openly teach a technique before an exercise. Practice
mode does not introduce the intended technique without permission.

Proposal: assistance follows a gradual ladder:

- Level 0: clarify the statement, requested syntax, or what the learner's code does.
- Level 1: ask a small question about an observation or failing example.
- Level 2: suggest a direction or relevant concept.
- Level 3: offer a concrete algorithm outline or pseudocode.
- Full reveal: show and discuss a solution only after an explicit request.

A generic request for a hint grants the next small step, not every remaining level.
Permission to view a solution is distinct from permission to edit an attempt.
Authorization is specific to the active problem and does not carry into another
problem or a later blank review.

Proposal: offer one check-in after two materially similar failed attempts, or
when Joe P explicitly expresses uncertainty. Suppress repeated offers after a
request for more time; offer again only on a meaningful new signal or a request.
These are responses to available session evidence, not background surveillance.

Recommendation descriptions, filenames shown to the learner, test output, notes,
and retrieved context should be reviewed for accidental technique disclosure.
Past notes can summarize support needs without displaying a prior solution.

## 6. Local test preparation and confidence

Confirmed: local tests should be realistic but cannot claim equivalence to
LeetCode's private system suite or execution environment.

Proposal: prepare tests before examining Joe P's attempt. Verify:

- The statement, allowed inputs, signature, return contract, and mutation rules.
- Examples, minimum inputs, constraint boundaries, and adversarial arrangements.
- Deterministic generated cases with recorded seeds.
- Independently validated expected results; use a simple brute-force oracle on
  smaller inputs when useful and feasible.
- Output predicates for multiple valid answers, ordering flexibility, floating
  tolerances, or in-place mutation when the problem requires them.
- Large-input behavior, with performance observations distinguished from correctness.

A reference implementation is a testing aid, not the only accepted algorithm.
Use problem-derived examples and independent cross-checks to validate the
reference; comparing two unverified implementations is insufficient evidence.

Preserve discovered regressions in the problem's suite. Version the test suite
so a past pass records exactly what was checked. Missing tests, exceptions,
unimplemented methods, and timeouts must never be reported as passes.
Local time limits protect against runaway execution; a timeout is evidence of
an unfinished test run, not a proof of a particular complexity class.

## 7. Explanation grading

Confirmed: score the explanation separately from test completion and efficiency
coaching. A clear explanation of a slower valid algorithm can earn full marks.
An explanation that is skipped is ungraded, not zero.

Approved rubric: use whole-number scores with evidence for each component:

| Component | Points | Evidence |
| --- | --- | --- |
| Approach | 0-4 | Accurately describes what the submitted code does |
| Correctness reasoning | 0-4 | Explains why it works, including relevant edge cases |
| Time complexity | 0-2 | Defines input size and accounts for dominant operations |
| Space complexity (bonus) | +0-1 | Briefly identifies significant auxiliary storage |

Confirmed: space complexity contributes only a separate bonus, not part of the
core 10. The approved core weights total 10: 4 approach, 4 correctness, and 2 time.
Report the core score and bonus separately, for example 9/10 plus 1 bonus.
Omitting space analysis does not reduce the core score. Give a brief component
breakdown, one strength, and the most useful correction.
Score the actual explanation, not its resemblance to reference wording. Record
whether an explanation was initial or revised after feedback. Hints used and
elapsed time do not automatically subtract explanation points.

## 8. Curriculum, adaptation, and review

Proposal: begin with easy problems involving arrays, strings, lookup structures,
then expand through sequence processing, linked structures, trees, graphs, and
dynamic programming as readiness develops. This is a teaching sequence rather
than a visible technique label attached to each practice recommendation.

Choose among a due review, a prerequisite gap, a related problem with a different
surface form, or the next curriculum objective. Use explanation evidence and
assistance history as well as passes; passing alone does not establish mastery.
Joe P can override any recommendation.

Approved starting review gaps: 1, 3, 7, 14, and 30 days. Reviews are suggestions
that Joe P can skip or reschedule. Advance an interval
after an independent successful review; shorten it after substantial help or
revealed misunderstandings. Missing a date incurs no penalty. A due review is a
recommendation shown during a session, not an automatic notification.
The exact scheduling rule should be finalized in the implementation plan.

## 9. Knowledge and progress records

Confirmed sharing boundary: personal attempts, progress, session notes, and
learner-specific generated context are local and excluded from Git by default.
Shared starters, exercise tests, published references, curriculum, and practice
tools are versioned. A fresh clone starts with no other learner's history and
initializes local state on first use. Both menus read and update that same local
state. Packaging and default RAG exports must also omit personal learner state.

Proposal: use plain Markdown for explanations and structured JSON for validated
metadata and progress. Keep one authoritative record for each fact; rendered
summaries are derived views, not separately editable copies of the same state.

Identify a problem by platform plus its platform-specific ID. Language belongs
to the attempt, adapter, and language-specific reference material, rather than
being part of the underlying problem identity.

Each attempt records its problem, language, mode, timing opt-in, code path,
assistance events, test evidence, explanation assessment, review outcome, and
any separately reported platform verdict. Derived views may summarize progress
by problem, concept, platform, or language.

Record progress automatically at meaningful points, including test results,
hints, grading, and session closure. Interrupted sessions can resume from the
last saved event; do not rely solely on a final goodbye message.

Solving a problem in Python does not automatically mark its Rust implementation
complete. Shared conceptual learning can still inform recommendations across
languages. Future language support adds starters, compilation/execution,
serialization adapters, and references while retaining shared problem metadata.

## 10. Content preparation and catalog refresh

Confirmed intended use: this is a noncommercial project.

Confirmed initial source pool:

| Role | Approved sources |
| --- | --- |
| Teaching | Runestone and Hello Algo |
| General DSA references | OpenDSA and TheAlgorithms |
| LeetCode implementations | NeetCode and walkccc |

Select and validate individual files as problems are prepared; preserve their
citations and applicable source terms. Source-pool approval does not authorize
bulk imports or resume implementation before the PDD specification and plan are agreed.

Confirmed storage requirement: keep reference code locally with citations to
published sources. Also research reusable general DSA teaching material and
algorithm implementations. Source selection and verification policy are a
planning prerequisite; do not import reference code until they are settled.

Proposal: each imported reference records publisher, exact file/version, source
URL, declared reuse terms and notices, approach, language, and local test evidence.
Distinguish verifiable platform acceptance from an author's acceptance claim.
Keep upstream code, adaptations, and agent-written additions distinguishable.
Confirmed preference: prefer published references, but publication is not a
readiness requirement. Clearly labeled agent-written references may fill gaps
under the same independent local validation standard. Do not invent publication
or acceptance evidence.

Confirmed preservation approach: store published reference code and its notices
unchanged, with local execution and test adapters kept separately. Identify any
adapted or agent-written implementation separately and document its provenance.
Confirmed validation standard: require local tests plus independent correctness
checks for reference code. Verified LeetCode acceptance is additional evidence
when available, not a prerequisite. Track publication, local validation, and
platform acceptance separately. Detailed import procedures belong in the
implementation plan; source research is recorded in reference-sources.md.

Catalog refresh retains IDs, titles, slugs, difficulty, access flags, source URL,
and fetch timestamp. Track preparation readiness separately from catalog metadata.
The snapshot fetched on 2026-10-28 contains 4,096 entries; counts may change.

Refreshing validates the response before replacing the snapshot. A failed refresh
preserves the existing snapshot and reports its age; it must not silently remove
problems or overwrite attempts. The unofficial endpoint used during discovery,
`https://leetcode.com/api/problems/all/`, is a data source, not a guaranteed
supported integration contract. Its `frontend_question_id` is the learner-visible ID
and differs from the internal `question_id`; keep them distinct.

`practice catalog refresh [--source URL] [--json]` publishes the validated snapshot,
field-level added/changed/removed diff, and durable pending coverage identities for
#15 in one catalog envelope via a staged, fsynced atomic replacement. Repeated
no-op refreshes retain pending changes/removals until coverage reconciliation.
OS locks serialize cooperating writers; failures preserve old bytes and downstream
data. See [the refresh contract](catalog-refresh.md) for validation, endpoint limits,
concurrency boundaries, JSON shape, and interruption recovery.

Store each problem statement as a link to LeetCode plus our own short original
summary (task, signature, constraints and original examples), not copied text.

Confirmed development scope: prepare the entire catalog through planned GitHub
work items, with the six starters as the first verified batch. This replaces an
on-demand-only preparation model. Use controlled batches and minimal parallelism
in accordance with Joe P's resource preferences. Catalog entries remain pending
until their actual material and tests meet readiness criteria.

The issue structure is full-catalog parent #1 with actual GitHub sub-issues for
individual problems or coherent classes, with further children as useful. Each
snapshot entry must map exactly once to a preparation ticket. Arbitrary batches
of 25 problems are not the default delivery unit. Starter tracking parent #8
contains six problem tickets #20–#25. Catalog access is #5; exhaustive mapping
and resumable issue creation are separately tracked by #15. Tracking parents do
not imply a single PR or a claim that all catalog entries are already mapped.

For each preparation task, the developer/agent obtains the available statement and official
language signature, prepares original learning notes and tests, validates the
adapter, and only then marks local practice ready. When required source material
is unavailable, request it or leave preparation pending instead of inventing it.
Catalog membership does not grant access to restricted statements or editorials.

## 11. Coding-agent instructions

Decision: a development CLAUDE.md carries repository development rules. The tutor
policy lives in a separate scoped file that only practice sessions load, so it never
hinders development agents. Keep tool-specific details small. Cursor users can
read the same tutor policy without making Cursor necessary for anyone else.

Repository instructions guide model behavior; they are not an access-control
boundary. Separate solution files and default context selection reduce accidental
spoilers, but behavioral compliance also needs real-session evaluation.

Official conventions checked on 2026-10-28:

- Codex discovers AGENTS.md along its directory instruction chain and supports
  AGENTS.override.md. Launch from the repository root for the intended context.
  https://learn.chatgpt.com/docs/agent-configuration/agents-md
- Claude Code supports CLAUDE.md and @path imports. Its documented AGENTS.md
  support depends on version and settings; a CLAUDE.md import remains a useful
  compatibility option. Check loaded instructions during setup.
  https://code.claude.com/docs/en/memory
- Cursor supports AGENTS.md and optional .cursor/rules/*.mdc project rules.
  This project can use its shared AGENTS.md without requiring Cursor-specific files.
  https://cursor.com/docs/rules
- LeetCode distinguishes user-selected runs from submission against its system
  test suite. A local pass cannot establish a platform verdict.
  https://support.leetcode.com/hc/en-us/articles/32442719377939-How-to-create-test-cases-on-LeetCode

## 12. RAG preparation and follow-up

Proposal: retain stable document IDs, problem identity, language where relevant,
content kind, source, version/hash, and spoiler level for each exportable chunk.
Default export includes public problem context only. Hints require the requested
level; solutions require explicit reveal. Attempts and personal progress are
excluded from the default knowledge export.

The follow-up experiment should compare direct repository context with retrieval
on grounded explanation quality, source attribution, and spoiler leakage. Filter
by problem, language, mode, and permitted reveal level before providing retrieved
content to the tutor. Keep personal learning memory distinct from general solution
knowledge. No embeddings service or vector database is required in the first release.

## 13. Proposed acceptance scenarios

1. Select a catalog problem or request a recommendation without requiring Cursor.
2. Complete a prepared Python exercise locally through both supported agents.
3. Request a small hint without receiving pseudocode or a full solution immediately.
4. Ask for a potentially revealing refresher and receive a permission check first.
5. Confirm that the tutor leaves the learner's attempt unchanged during normal help.
6. Pass tests with a valid alternative algorithm and receive appropriate feedback.
7. Explain an O(n^2) solution accurately, earn a strong explanation score, and
   receive gradual optimization coaching where a faster approach exists.
8. Record local completion without inventing LeetCode acceptance.
9. Resume an interrupted session with saved progress and preserved code.
10. Start a blank review while preserving and withholding earlier solution code.
11. Start an ordinary session untimed, even after previously using timed practice.
12. Detect a known implementation defect with the realistic local suite; confirm
    that an empty suite or unimplemented starter cannot report completion.
13. Keep existing work intact when starting the same problem or refreshing catalog data.
14. Export default RAG context without solutions, attempts, or personal progress.
15. Record platform and language explicitly so future platforms and languages
    can be added without changing problem identity or conflating attempt outcomes.

Use unit, integration, and end-to-end tests with real local files and processes.
Verify strict Python type checking, configured lint and formatting checks, the
full suite, and logs. Use live agent sessions to assess tutor behavior; deterministic
file tests alone do not establish that a model follows the policy.

## 14. Planning and delivery status

The release outline, source pool and validation policy, 4/4/2 grading rubric with
separate space bonus, starting review schedule, and implementation defaults are
agreed. Deliverable-specific schemas and adapter details are finalized in their
own ticket contracts before implementation, preserving the agreed behavior.

The ticket-based, test-first implementation plan is in implementation-plan.md.
Planning defaults and score anchors were approved, and tickets are reconciled around
separate deliverables and actual sub-issue hierarchies. Implementation proceeds
ticket by ticket in dependency order.
