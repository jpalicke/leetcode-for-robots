# Spaced review

Reviews bring a problem back after a gap so you redo it from a blank file. They
are derived, never stored: `practice review list` folds the journal
(`.practice/journal.jsonl`) from the top each time. The journal stays the only
source of truth. Skips and reschedules are journal events too.

Nothing runs in the background and nothing sends a reminder. Run
`practice review list` (or open Reviews in a menu) to see what is due. A review
never costs score, whether it is late, skipped or rescheduled.

## What makes a problem review-eligible

An attempt of the problem has at least one passing local run, in any mode. The
first such attempt starts the review track at the shortest gap, however much help
it had. A track is one platform, problem and language together, so Python reviews
stay apart from any other language, and two platforms never mix.

## The ladder

The gaps are the constants `GAP_DAYS` in `src/practice/reviews.py`, the only place
they are written down.

| rung | gap |
| --- | --- |
| 1 | 1 day |
| 2 | 3 days |
| 3 | 7 days |
| 4 | 14 days |
| 5 | 30 days |

The due date is the day of the passing run (UTC calendar day) plus the gap for the
current rung. It is counted from when you actually practiced, so a late review
does not shorten the next wait.

## What moves the ladder

Only attempts started with `practice review start` move it. An ordinary later
attempt of the same problem is kept in history but does not change the schedule.
When a review attempt first passes, only help recorded before that pass counts:

| what happened | result |
| --- | --- |
| no help, the pass still current | up one rung (stays at 30 days at the top) |
| concept help, or the passing code was edited afterwards | same rung |
| one or more hints | down one rung (never below 1 day) |
| the solution was revealed | back to rung 1 |
| the latest fully graded explanation scored under `EXPLANATION_CORE_THRESHOLD` (7 of the core 10) | back to rung 1 |

A partial or ungraded explanation is never held against you. A review that has not
passed yet does not change the schedule.

## Commands

```text
practice review list
practice review start PLATFORM ID [--language python] [--package DIR]
practice review skip PLATFORM ID [--language python]
practice review reschedule PLATFORM ID (--on YYYY-MM-DD | --in-days N) [--language python]
```

- `list` shows what is due now and what is upcoming, each with its date, rung and
  gap, and any review attempt still open.
- `start` is `attempt start` with a review marker. The file is the package starter,
  never prefilled. Earlier solutions stay on disk, and no earlier code is printed.
  Starting early is allowed and says so. If a review attempt is already open it
  refuses and points to `practice attempt resume`. Because it is a normal attempt,
  `attempt test`, `resume`, `note-assistance`, `notes` and the menus all work.
- `skip` records `review_skipped`. The next date is the skip day plus the current
  gap and the rung is unchanged.
- `reschedule` records `review_rescheduled` with an exact date, from `--on` or
  `--in-days` (a past date is refused). The latest event wins, and a new review
  pass replaces any earlier skip or reschedule.

A problem with no passing run has no review, so all four refuse it with exit 2.

## The clock

"Now" comes from one function, `practice.clock.now()`. Set `PRACTICE_NOW` to an ISO
timestamp, such as `2026-11-02T09:00:00Z`, to pretend it is that moment; a time
without an offset is read as UTC. Unset or empty means the real clock, and an
invalid value stops the command with exit 2. Tests drive multi-day scenarios with
it in a real subprocess environment.
