# Recommendations

`practice recommend` suggests what to practice next from the curriculum and the
learner journal (`.practice/journal.jsonl`). Nothing is stored: the answer is derived
from the journal each time, so the journal stays the only source of truth.

```text
practice recommend                 one primary pick and up to three alternatives
practice recommend --json          the same, for tools
practice recommend --choose N      show pick N in full (1 is the primary)
practice menu --recommend          the same core as a numbered menu screen
```

It never starts anything and never writes to the journal. To act on a pick, run the
command it prints (`practice attempt start`, `practice attempt resume` or
`practice review start`), or choose the matching item in the menu. You can always
start any other problem; a recommendation is only a suggestion.

## Priority

The order is the list `REASONS` in `src/practice/recommendations.py`, the only place
it is written down. A problem appears once, under its highest priority reason.

1. Unfinished attempt to resume: an open attempt with no passing run yet. The newest
   comes first.
2. Due review: a blank review that is due (see `docs/spaced-review.md`), ordered by
   due date, then problem.
3. Prerequisite gap: a problem you have already tried but not solved independently
   depends on earlier material. The earlier problems that are not solved
   independently are suggested first, in curriculum order.
4. Next curriculum objective: the next objective whose prerequisites are done,
   in curriculum order.

Tie-breaking is deterministic. Within one reason the order is fixed (see above) and
there is no randomness. The only clock is `PRACTICE_NOW` (see `src/practice/clock.py`),
so the same journal and the same date always give the same answer.

## Reasons the learner sees

The reason is one of: "unfinished attempt to resume", "due review", "prerequisite
gap", "next curriculum objective". It comes with one plain sentence, for example
"It is part of Objective 1." Labels are the problem title and difficulty only. A
recommendation never names a technique or an internal curriculum key.

## Evidence and mastery

Each pick shows what the journal says about the problem:

- No attempts yet.
- Attempted without a local pass yet.
- A pass is on record, but the code changed since (a stale pass). It does not count.
- Passed with help, with the counts of each kind of help given before the pass.
- Passed independently: no help before the pass and the code unchanged since.
- Mastered.

A passing test run alone is not mastery. A problem is mastered when it has an
independent pass and its explanation scored not low (a core total of at least 7 out
of 10), or when its latest blank review passed independently. A later review that
needed help withdraws mastery. A low explanation keeps an independent pass
unmastered, and the evidence line says so.

Progression needs an independent pass: a concept counts as done when every ready
problem in it was solved independently. Mastery is reported separately and drives
the review ladder.

## Only ready problems

Only problems with a ready exercise package are recommended. The rest are pending
and are counted ("N curriculum problem(s) are waiting for ready exercises."), never
offered. A concept with no ready problem is skipped so pending content never stalls
progress.

## When there is nothing to recommend

The command says so plainly and exits 0, because having nothing to suggest is an
answer. The message tells you whether problems are still waiting for ready exercises
or everything available is solved with no review due.

## Exit codes

| code | meaning |
| --- | --- |
| 0 | A recommendation, or a plain "nothing to recommend" |
| 2 | Usage error: bad `PRACTICE_NOW`, or `--choose N` out of range |
| 3 | Bad input: an unreadable catalog, curriculum or journal |

(The numbers come from `src/practice/exit_codes.py`.)
