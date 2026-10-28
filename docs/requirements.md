# DSA practice: requirements discovery

Status: requirements captured; specification under review. Implementation remains paused.
This document records decisions, not authorization to begin implementation.

## Purpose and process

Build a Python DSA practice repository usable with Codex and Claude Code.
Support both rebuilding DSA fundamentals and preparing for technical interviews.
The project is intended for noncommercial use. Noncommercial-licensed reference
material can be considered, subject to its applicable source terms.
Follow Prompt-Driven Development: discover requirements, agree on a specification,
prepare an implementation plan, then build with verification.

## Development agent preferences

For development work on this project, prefer Sol for the main agent and delegated
work. Use Luna for suitable lightweight tasks. Do not use Astra High or raise
reasoning effort without Joe P's explicit approval. Minimize unnecessary parallel
agents to conserve session limits. These preferences do not require learners to
use a particular tutor model or editor.

## Confirmed decisions

### Catalog and problem selection

- Cover the full LeetCode catalog and prepare its questions as planned development
  tasks reflected in GitHub issues. Preparation is not limited to questions Joe P
  selects during practice and does not imply running every task simultaneously.
- Catalog coverage does not imply every problem has verified local tests or solutions.
- Start with easy Python practice while allowing selection from the whole catalog.
- Six prepared easy Python problems form the first validated batch. Include
  preparation of the remaining catalog in the development backlog, with explicit
  readiness criteria and tracked blockers rather than relying on on-demand work.
- Joe P can choose a problem or ask the tutor to recommend one.
- Recommendations combine a structured curriculum with adaptation to practice
  history, weak spots, and review needs.

### Language scope and future refinements

- Python is the first-release practice language.
- C++, Rust, and Go are future refinements; their execution support is outside
  the first-release scope.
- Design implication for the specification: preserve shared problem identity,
  tutoring policy, and learning history while separating language-specific
  starter code, test adapters, toolchains, and attempts.
- Progress records should identify the language used. Do not assume solving a
  problem in one language establishes implementation proficiency in another.

### Platform stretch goals

- LeetCode is the first-release platform.
- CodeFights and HackerRank are stretch goals; their integrations are outside
  the first-release scope.
- Design implication to carry into the specification: identify each problem by
  its platform and platform-specific ID, and keep shared tutoring and learning
  history usable across platforms.
- Verify each platform's current offerings and integration options before
  planning its implementation.

### Practice environment

- Local coding is the primary workflow, independent of a particular editor.
- Cursor remains an optional choice for anyone who wants to use it. The
  repository must work fully without Cursor or dependence on its features.
- Preserve support for Codex and Claude Code.
- Use LeetCode for submission; browser practice can work by sharing code and results.
- Browser observation and continuous monitoring are not agreed capabilities.
- The tutor uses code, results, and conversation available in the active session.

### Menus and navigation

- Provide both a numbered menu in the tutor chat and an interactive terminal menu.
- Offer resume, recommendation, problem browsing/selection, due reviews, study,
  progress/notes, and explicitly optional timed practice.
- Offer contextual actions during a problem, including running tests, requesting
  a hint, explaining the solution, and returning to the main menu.
- Both menus use the same active attempt and authoritative progress records.
  Free-text requests remain available in the tutor chat.
- For conversational actions, the terminal menu prepares a request for Joe P to
  paste into an existing coding-agent chat. Include the relevant problem/attempt,
  selected action, mode, and permitted assistance level without leaking solutions.
- Preparing a request does not itself deliver tutor assistance; record actual
  hints or reveals when the coding agent provides them.

### Learning modes and refresher boundaries

- Support study mode and practice mode, with practice mode as the default.
- In study mode, openly teach a concept before practicing it; knowing the
  technique is an intended part of that experience.
- In practice mode, present the problem without naming its intended technique.
  Refreshers are available on request.
- A refresher that suggests a solution strategy counts as a hint. Ask before
  proceeding when an explanation could reveal an approach.
- Explain requested Python syntax or information already in the problem without
  introducing an unsolicited strategy.
- Apply spoiler awareness to recommendation labels and context selection as
  well as tutor responses, so technique names do not inadvertently give hints.

### Optional timed practice

- Timed interview practice is strictly optional and requires explicit opt-in for
  that session; do not enable it automatically as the learner progresses.
- Ordinary practice, study, and spaced review remain untimed by default.
- Timing is a separate session setting from practice versus study mode.
- Keep timing feedback separate from the explanation score. Untimed sessions
  carry no speed penalty.

### Tutor behavior

- Joe P types the solution. Default assistance uses questions, explanations,
  and gradual hints.
- Editing Joe P's solution is a last resort, requiring an explicit request after
  other assistance has not helped.
- Full solutions stay hidden until explicitly requested. Asking for a hint does
  not authorize revealing a full solution.
- Gentle check-ins are welcome when observable interactions suggest difficulty:
  recurring failures, revisions with the same issue, an explanation revealing
  confusion, or Joe P saying he is stuck.
- Silence alone is not evidence of struggle. Trigger thresholds remain open.
- Evaluate alternative solutions on their merits; do not require matching a
  single reference implementation.
- A correct slower solution can prompt gradual optimization coaching. Invite
  examination of repeated work before revealing a faster approach.

### Completion and explanation grading

- Passing the realistic local test suite marks a problem complete locally.
- Track LeetCode submission and acceptance independently; acceptance is not a
  prerequisite for local completion or explanation grading.
- Keep local results, platform results, and explanation scores distinct. A local
  pass does not imply LeetCode acceptance.
- After passing, invite Joe P to explain his approach and time complexity.
- Grade the explanation with a core score out of 10 and brief feedback.
- Approved core rubric: approach 4 points, correctness reasoning (why it works)
  4 points, and time-complexity analysis 2 points.
- Space-complexity analysis earns up to one separate bonus point; it is not part
  of the core 10. Report the core score and bonus separately (for example,
  9/10 plus 1 bonus), so omitting space analysis does not reduce the core score.
- Weight explaining the approach and why it works more heavily than time-complexity
  analysis. Discuss meaningful space tradeoffs when useful.
- An accurate explanation of a slower correct solution can earn a strong score.
  Efficiency coaching is separate from explanation accuracy.
- The explanation exercise does not block completion earned by passing tests.

### Published references and local storage

- Store reference code inside the repository alongside citations to published
  sources; links alone do not meet the reference-storage requirement.
- Research reusable open-source DSA reference material as well as problem-specific
  solutions, including explanations, teaching texts, and algorithm implementations.
- Source selection and the required verification standard must be settled before
  importing reference code or resuming implementation.
- Prefer published reference implementations, but do not require them before a
  problem is ready. Agent-written references can fill gaps, with clear provenance
  labels and the same independent local validation standard.
- Cite actual published sources when used; do not invent a publication or
  acceptance claim for agent-written material.
- Preserve published reference implementations and their notices unchanged.
  Keep local execution/test adapters separate from those preserved sources.
- Label any adapted or agent-written implementation separately and record its
  relationship to the published source rather than silently editing that source.
- Approved initial source pool: Runestone and Hello Algo for teaching; OpenDSA
  and TheAlgorithms for general DSA references; NeetCode and walkccc for
  LeetCode-specific implementations. Select and validate individual files as
  problems are prepared, preserving their citations and applicable source terms.
- Require local tests and independent correctness checks for reference code.
  Verified LeetCode acceptance is additional evidence when available, not a
  prerequisite. Record publication, local validation, and platform evidence separately.
- Detailed import procedures belong in the implementation plan.

### Local testing standard

- Build suites from each problem's requirements and permitted input constraints,
  independently of Joe P's attempted solution.
- Include examples, boundary cases, adversarial cases, reproducible generated
  cases, correctness properties, and large-input performance checks.
- Validate generated expected results with independently verified reference
  implementations; simple brute-force checks can serve smaller inputs.
- Accept alternative valid outputs when the problem permits multiple answers.
- Local performance measurements provide evidence and do not claim to reproduce
  LeetCode's execution environment or hidden system test suite.
- When an available platform failure reveals a useful case, preserve it locally
  for subsequent testing and review.

### Progress and review

- Automatically save approach, test results, hints used, explanation score, and
  suggested review topics in session notes.
- Use notes to support continuity and future recommendations.
- Exclude personal attempts, progress records, session notes, and generated
  learner context from Git by default, so others can clone a clean practice repository.
- Keep shared starters, tests, reference material, curriculum, and practice tools
  versioned. Each clone initializes its own local learner history.
- Include spaced review by re-solving selected problems from a blank attempt.
- During review, keep earlier solutions hidden until requested.
- Approved starting review gaps: 1, 3, 7, 14, and 30 days, adjusted according to
  independent success or assistance needed. Reviews are suggestions and may be
  skipped or rescheduled; missed dates carry no penalty.
- Mastery criteria and detailed scheduling mechanics belong in the implementation plan.

### RAG preparation

- Structure repository knowledge for a fast-follow RAG experiment.
- The first version works through coding agents and repository files.
- Retrieval design, content boundaries, and the follow-up experiment remain open.

## Evidence gathered

- The public catalog response downloaded on 2026-10-28 reports 4,096 entries.
  This is a dated snapshot, not a fixed catalog size.
- Current official instruction documentation was checked for Codex, Cursor,
  and Claude Code. Final adapters and citations belong in the specification.
- The repository has been initialized with a work branch. No implementation
  files have been created.

## Remaining specification and implementation details

- Verify problem-source acquisition and Python signatures, including adapters
  for custom data structures and problems requiring specialized execution.
- Define score anchors within the approved 4/4/2 core rubric and separate bonus.
- Specify recommendation, mastery, and adaptive-review mechanics using the agreed schedule.
- Turn tutor behavior, spoiler boundaries, and check-ins into concrete acceptance scenarios.
- Review the proposed helper workflow, progress schema, and RAG export boundaries.
- Break the agreed specification into test-first work items before implementation.

Before implementation, turn agreed requirements into a specification and a
sequence of small, testable work items for Joe P to review.
