# Curriculum and prerequisites

`curriculum/core.json` is the versioned source of truth for concept order,
prerequisites, the six selected starter problems and their placements. It is
validated against the real committed catalog, independently of exercise packages.

```text
uv run --locked practice curriculum check
uv run --locked practice curriculum next
uv run --locked practice curriculum next --json
uv run --locked practice curriculum check --file curriculum/core.json --json
uv run --locked practice --catalog catalog/leetcode.json curriculum next --file curriculum/core.json
```

With no learning history, `next` prints:

```text
Objective 1
  leetcode/1: Two Sum
```

This is curriculum eligibility, not a claim that every listed problem has a
runnable exercise package. Check `practice readiness leetcode ID` before starting
an exercise. Reading the map creates no learner state. Exit codes are 0 for a
valid map/query, 2 for CLI usage errors and 3 for invalid or unreadable data.

## Internal map

The `concepts` array gives the canonical order below. Prerequisites express the
chosen teaching progression, not universal mathematical dependencies.

| Internal concept | Direct prerequisites |
| --- | --- |
| Arrays | None |
| Strings | Arrays |
| Lookup structures | Arrays |
| Sequence processing | Arrays, strings, lookup structures |
| Linked structures | Sequence processing |
| Trees | Linked structures |
| Graphs | Trees, lookup structures |
| Dynamic programming | Graphs, sequence processing |

| Starter | Placement | Explicit prerequisites |
| --- | --- | --- |
| LC1 Two Sum | Arrays | None |
| LC217 Contains Duplicate | Lookup structures | Arrays |
| LC242 Valid Anagram | Strings | Arrays |
| LC20 Valid Parentheses | Sequence processing | Arrays, strings, lookup structures |
| LC704 Binary Search | Sequence processing | Arrays, strings, lookup structures |
| LC121 Best Time to Buy and Sell Stock | Sequence processing | Arrays, strings, lookup structures |

Learning objectives never mandate a canonical optimized algorithm. For example,
Two Sum can start with enumeration of index pairs. Placement records describe
what to practice; exercise correctness remains the package's responsibility.

Schema version 1 declares `platform`, which must match the catalog platform,
and has a nonempty ordered `concepts` list of records with `id`,
`name`, and explicit `prerequisites`; a nonempty ordered `starters` list of positive
catalog problem IDs; and `placements` records with `problem_id`, `concept`, and
explicit `prerequisites`. The chosen catalog supplies the platform and authoritative
problem titles. Each selected starter has exactly one placement. Placement
prerequisites include its concept's direct prerequisites and precede the target
concept. Unknown references, duplicate IDs or prerequisites, duplicate/extra/missing
placements, prerequisite cycles, and out-of-order prerequisite definitions are
rejected. The schema allows later additions; committed-data tests pin all six
required starters.

Concept order determines stable numbered objective labels. The starter selection
array determines problem order within objectives, regardless of placement-record
order. Sets are used only for membership checks, never to order public results.

## Context and reveal boundary

The map and this developer document name concepts and techniques and belong to
internal curriculum context. They are not learner prompts or study lessons.
`practice curriculum next`, including its JSON form, projects only numbered
objective labels and catalog platform/problem ID/title fields. It ignores free-form
placement labels; custom curriculum names cannot become learner-facing hints.
Canonical problem titles remain visible, including titles that name a technique.
`check --json` returns validation status and counts without concept details.

The engine's `next_objectives(mastered=...)` accepts internal concept IDs from
future callers. It returns unmastered concepts whose direct prerequisites are
mastered, and associated problems whose explicit prerequisites are mastered.
Callers supply their own mastery assertions; this ticket neither infers them from
attempts nor reads history. Empty objectives are allowed for concepts whose
exercise selection is still pending. Recommendation scheduling/history adaptation,
study lessons and menu integration belong to separate tickets.
