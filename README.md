# leetcode-for-robots

Practice data structures and algorithms locally with a coding-agent tutor.
The learner writes the solution; the tutor offers questions, gradual hints,
realistic tests, explanation feedback, and review suggestions.

**Status: development tooling.** Python setup and quality-gate tests are available.
The practice tools and exercise packages are not implemented. Development follows
the reviewed PDD plan, with approval and verification gates between phases.

See [development setup](docs/development.md) to install dependencies and run checks.

## Planning documents

- [Requirements and agreed decisions](docs/requirements.md)
- [Specification draft](docs/specification.md)
- [Published reference research and source policy](docs/reference-sources.md)
- [Development backlog proposal](docs/development-backlog.md)
- [Phased implementation plan](docs/implementation-plan.md)

## Planned scope

- Python first, with Codex and Claude Code support and an editor-independent workflow.
  Cursor remains an optional choice.
- Both a tutor-chat menu and a terminal menu. Terminal tutoring actions prepare
  requests to paste into an existing agent chat.
- Full LeetCode catalog coverage, with preparation tracked as development tasks
  in GitHub issues. Six easy exercises form the first validated batch.
- Study and practice modes; timed practice is strictly optional.
- Local completion, explanation grading, and LeetCode acceptance tracked separately.
- Personal attempts, progress, notes, and generated requests excluded from Git by default.
- Locally stored reference code with citations, preserved source notices, and
  independent validation; published implementations are preferred.
- A structure ready for a follow-up RAG experiment.

The project is intended for noncommercial use. Selected third-party reference
material retains its own license and attribution requirements.

Future refinements include C++, Rust, Go, CodeFights, and HackerRank.
