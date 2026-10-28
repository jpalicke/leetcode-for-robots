# Development backlog proposal

Prepared for Joe P. Planning only; implementation remains paused.
GitHub destination: [jpalicke/leetcode-for-robots](https://github.com/jpalicke/leetcode-for-robots). No issues have been created yet.

## Agreed scope change

Preparing all LeetCode questions is development work to be represented in GitHub
issues. It is not work deferred until a learner selects a question, and it does
not require running every preparation task simultaneously. The six easy starters
are the first verified batch; the full catalog has an explicit preparation backlog.

The catalog response obtained on 2026-10-28 reports 4,096 entries. Coverage must be
measured against a named snapshot, with later additions reconciled explicitly.
A catalog listing, an open task, and a validated ready exercise are different states.

## Proposed issue structure

- One parent issue for full-catalog preparation and its coverage report.
- Bounded preparation-batch issues with a per-problem checklist. A starting limit
  of 25 ordinary problems per issue is proposed; specialized problems can use
  smaller batches or dedicated issues.
- Separate issues for reusable infrastructure, adapters, source intake, and
  validation features shared across batches.
- Focused blocker issues where source access, licensing evidence, execution
  contracts, or specialized platform behavior prevents readiness.
- Each catalog entry maps to a batch or focused task, without silently omitting
  premium, non-Python, interactive, SQL, or shell entries. Any unsupported scope
  remains explicitly pending or blocked and never falsely marked Python-ready.

This keeps every question accountable without requiring thousands of individual
issue creations. Batch granularity remains a proposal for review. GitHub is the
work tracker; validated repository metadata is the authority for practice readiness.
An issue closes only when its deliverables and verification evidence are present.

## Proposed workstreams

| Workstream / parent issue | Development tasks | Completion evidence |
| --- | --- | --- |
| Repository foundation and tutor contract | Shared agent instructions; project tooling; private learner-state boundary; source manifest contract | Supported agents load policy; strict checks configured; clean clone starts with no personal history |
| Catalog and preparation inventory | Validated snapshot; IDs and source metadata; readiness states; exhaustive mapping into preparation batches | Every snapshot entry has a tracked preparation task; refresh preserves work and identifies additions |
| Published source intake | Select files from the six approved sources; preserve code/notices; pin versions; adapters and independent validation | Provenance, applicable notices, executable contract, and local validation recorded; acceptance claims distinguished |
| First verified exercise batch | Two Sum; Contains Duplicate; Valid Anagram; Valid Parentheses; Binary Search; Best Time to Buy and Sell Stock | Six complete exercise packages satisfy the per-problem checklist below |
| Full-catalog preparation | Create bounded batches covering remaining entries; prepare and verify each package | Coverage report distinguishes ready, in progress, pending, and blocked for the complete snapshot |
| Specialized execution formats | Typed nodes and serialization; mutation/custom outputs; stateful design problems; interactive contracts; non-Python scope inventory | Contract-specific tests; explicit support boundaries; no empty-suite or generic-stub passes |
| Menus and tutor-request handoff | Chat menu; terminal menu; browse/resume/test/progress actions; paste-ready requests | Same active state from both menus; requests contain permitted context and no unintended solution |
| Progress, grading, and reviews | Ignored local state; automatic notes; 4/4/2 rubric plus space bonus; adaptive review gaps | Resume, scoring, review, code-version tracking, and clean-clone scenarios pass |
| RAG-ready knowledge preparation | Source-aware chunks; mode/reveal classification; deterministic export | Default export excludes solutions and learner state; provenance remains attached |
| RAG follow-up and stretch tracks | Retrieval experiment; C++, Rust, Go; CodeFights and HackerRank | Separate milestones and acceptance criteria, without implying support in the first Python release |

These workstreams are a backlog structure, not permission to execute them all or
an assertion that every workstream fits in one implementation phase. The phased
plan will break them into small, test-first tasks and state dependencies/file scope.

## Per-problem preparation checklist

Use this acceptance checklist in each preparation batch:

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

A batch is complete only when each listed problem meets this checklist or the
batch is explicitly split to retain unresolved work in open issues. Moving a
problem to a blocker issue does not count it as ready in the coverage report.

## Batch issue body proposal

Each issue should identify:

1. Catalog snapshot/version and the exact problem IDs in scope.
2. Prerequisite infrastructure/adapters and approved source candidates.
3. A per-problem readiness checklist and links to any blockers.
4. Expected repository outputs and verification commands/evidence.
5. Dependencies, milestone, and definition of done.

Use meaningful titles such as "Prepare LeetCode Python batch: [problem range or
explicit selection]". Actual issue titles, IDs, repository, labels, and milestones
will be resolved before posting; none are invented here as existing GitHub state.

## Execution preferences

Prefer Sol for implementation and delegated work. Luna may handle suitable
lightweight metadata/checklist tasks. Minimize unnecessary parallel agents.
Do not use Astra High or increase reasoning effort without explicit approval.
Use the agreed PDD and TDD process; no implementation resumes until the
specification and phased plan have been reviewed. Follow the phase/file limits
and verification gates in Joe P's project instructions.
