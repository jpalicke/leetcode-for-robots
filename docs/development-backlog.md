# Development backlog

Prepared for Joe P on 2026-10-28. Implementation is paused during plan reconciliation.
[Repository](https://github.com/jpalicke/leetcode-for-robots) and
[implementation plan](implementation-plan.md).

## Work organization

Implementation tickets deliver separate testable outcomes, normally one PR each.
A PR handles one ticket. Internal phases are implementation details. No fixed
file-count or problem-count limit applies. Open PRs ready for review after work
and checks finish; drafts require Joe P's explicit request.

Use actual GitHub sub-issues under [full catalog #1](https://github.com/jpalicke/leetcode-for-robots/issues/1)
for individual LC problems and coherent classes. Tracking parents need no single
PR; their children deliver the work. The starter group #8 contains six individual
problem tickets. Keep infrastructure dependencies separate from problem readiness.

The discovery snapshot has 4,096 entries as of 2026-10-28. Validate and reconcile
its complete mapping through the coverage-tracking ticket. Pending, blocked and
ready are distinct. Do not omit premium, specialized, SQL or shell entries.
A listed task is not a validated exercise. No arbitrary 25-problem batch default.

## Issue index

| Issue | Outcome | Kind |
| --- | --- | --- |
| [#1](https://github.com/jpalicke/leetcode-for-robots/issues/1) | Prepare the full LeetCode catalog as development tasks | Tracking parent |
| [#3](https://github.com/jpalicke/leetcode-for-robots/issues/3) | Reconcile the PDD plan and deliverable-sized GitHub backlog | Planning deliverable |
| [#4](https://github.com/jpalicke/leetcode-for-robots/issues/4) | Establish locked Python development tooling | Complete; PR #13 awaits merge |
| [#5](https://github.com/jpalicke/leetcode-for-robots/issues/5) | Provide a searchable LeetCode catalog with safe refresh | Implementation/discovery deliverable |
| [#6](https://github.com/jpalicke/leetcode-for-robots/issues/6) | Preserve published references with provenance and source notices | Implementation/discovery deliverable |
| [#7](https://github.com/jpalicke/leetcode-for-robots/issues/7) | Run ordinary Python exercise contracts reliably | Implementation/discovery deliverable |
| [#8](https://github.com/jpalicke/leetcode-for-robots/issues/8) | Track the first six verified Python exercise packages | Tracking parent |
| [#9](https://github.com/jpalicke/leetcode-for-robots/issues/9) | Provide shared tutor-chat and terminal navigation | Implementation/discovery deliverable |
| [#10](https://github.com/jpalicke/leetcode-for-robots/issues/10) | Preserve private attempts and resumable learner history | Implementation/discovery deliverable |
| [#11](https://github.com/jpalicke/leetcode-for-robots/issues/11) | Export deterministic source-aware knowledge with reveal filtering | Implementation/discovery deliverable |
| [#12](https://github.com/jpalicke/leetcode-for-robots/issues/12) | Track future retrieval, language and platform refinements | Tracking parent |
| [#14](https://github.com/jpalicke/leetcode-for-robots/issues/14) | Define and verify the shared coding-agent tutor contract | Implementation/discovery deliverable |
| [#15](https://github.com/jpalicke/leetcode-for-robots/issues/15) | Track every catalog problem through GitHub preparation sub-issues | Implementation/discovery deliverable |
| [#16](https://github.com/jpalicke/leetcode-for-robots/issues/16) | Generate spoiler-aware requests for an existing tutor chat | Implementation/discovery deliverable |
| [#17](https://github.com/jpalicke/leetcode-for-robots/issues/17) | Record explanation assessments separately from completion and optimization | Implementation/discovery deliverable |
| [#18](https://github.com/jpalicke/leetcode-for-robots/issues/18) | Schedule adaptive blank-attempt spaced reviews | Implementation/discovery deliverable |
| [#19](https://github.com/jpalicke/leetcode-for-robots/issues/19) | Recommend practice from curriculum and learner evidence | Implementation/discovery deliverable |
| [#20](https://github.com/jpalicke/leetcode-for-robots/issues/20) | Prepare LeetCode 1: Two Sum (Python) | Implementation/discovery deliverable |
| [#21](https://github.com/jpalicke/leetcode-for-robots/issues/21) | Prepare LeetCode 217: Contains Duplicate (Python) | Implementation/discovery deliverable |
| [#22](https://github.com/jpalicke/leetcode-for-robots/issues/22) | Prepare LeetCode 242: Valid Anagram (Python) | Implementation/discovery deliverable |
| [#23](https://github.com/jpalicke/leetcode-for-robots/issues/23) | Prepare LeetCode 20: Valid Parentheses (Python) | Implementation/discovery deliverable |
| [#24](https://github.com/jpalicke/leetcode-for-robots/issues/24) | Prepare LeetCode 704: Binary Search (Python) | Implementation/discovery deliverable |
| [#25](https://github.com/jpalicke/leetcode-for-robots/issues/25) | Prepare LeetCode 121: Best Time to Buy and Sell Stock (Python) | Implementation/discovery deliverable |
| [#26](https://github.com/jpalicke/leetcode-for-robots/issues/26) | Design the RAG comparison experiment | Implementation/discovery deliverable |
| [#27](https://github.com/jpalicke/leetcode-for-robots/issues/27) | Scope C++ practice support | Implementation/discovery deliverable |
| [#28](https://github.com/jpalicke/leetcode-for-robots/issues/28) | Scope Rust practice support | Implementation/discovery deliverable |
| [#29](https://github.com/jpalicke/leetcode-for-robots/issues/29) | Scope Go practice support | Implementation/discovery deliverable |
| [#30](https://github.com/jpalicke/leetcode-for-robots/issues/30) | Research CodeFights platform support | Implementation/discovery deliverable |
| [#31](https://github.com/jpalicke/leetcode-for-robots/issues/31) | Research HackerRank platform support | Implementation/discovery deliverable |

Verified hierarchy: #1 → #8 → #20–#25; #12 → #26–#31. #15 remains
open for the full snapshot mapping. Issue #4 was closed after its completion
comment; PR #13 is ready for review and not yet merged.

## Per-problem preparation checklist

Use this acceptance checklist in each problem or coherent class preparation ticket:

- Correct platform ID, slug/title, source link, difficulty, and language scope.
- Verified available statement, constraints, callable signature, and output/mutation contract.
- A blank learner starter in shared material; personal attempts remain ignored.
- A locally stored reference implementation, preferring a published source when
  available. Agent-written alternatives are allowed with explicit provenance.
- Published source code/notices preserved; local adapters and adaptations distinguished.
- Source citations, revision/hash, applicable terms, and verification evidence recorded.
- Explanation of correctness, complexity, pitfalls, and meaningful alternatives.
- Gradual hints and reference material classified so practice context does not
  reveal intended techniques without permission.
- Tests derived independently of the learner's code: examples, boundaries,
  adversarial cases, reproducible generated cases, and practical performance checks.
- Independent correctness checks for the reference; valid alternate outputs supported.
- Actual execution completed successfully. Missing tests, exceptions, stubs, and
  timeouts do not count as successful preparation.
- Local validation and platform acceptance recorded separately. Verified LeetCode
  acceptance is additional evidence, not a readiness prerequisite.
- Any unavailable material or unsupported execution requirement has a visible blocker.

A class ticket is complete only when each listed problem meets this checklist or the
scope is explicitly split to retain unresolved work in open issues. Moving a
problem to a blocker issue does not count it as ready in the coverage report.

## Ticket completion

Before closing a complete ticket, add a plain-English comment explaining the
work delivered and validation results. Link relevant PRs and reference sources,
and state whether the PR is merged or awaits merge. Then close as completed.
Do not wait for merge solely to close implemented and verified work. Do not close
unfinished work or a tracking parent with unmet scope as completed.

Each problem ticket identifies exact platform/problem IDs, source/snapshot,
prerequisites, expected package outputs, independent verification and readiness
criteria. Grouping tickets list their children and aggregate coverage; they do
not replace independently deliverable problem/class tickets.

Prefer Sol and minimal delegation; Luna only where appropriate. No reasoning
escalation or Astra High without explicit approval. Keep attempts, notes,
progress and generated requests local and Git-ignored. Full-catalog preparation
is planned development work, not work deferred until a learner chooses a problem.
