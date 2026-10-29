# Optional timed practice

Timing is off unless you turn it on for one attempt. It is evidence for you to look
at. It never changes what the tutor or the tools conclude about your understanding.

## Turning it on

```text
uv run --locked practice attempt start PLATFORM ID --timed [--limit-minutes N]
```

- `--timed` is the only way to time an attempt. `--limit-minutes` is optional and
  needs `--timed`; it must be a positive whole number.
- Timing is separate from practice or study mode. `--mode study --timed` is a valid
  pair of independent choices.
- It applies to that attempt only. The next `attempt start` is untimed unless you
  pass `--timed` again. Resuming, finishing, testing and reviews never switch it on.
- From the menus: main menu "Timed practice" opens the problem list in timed mode,
  and a problem's menu offers "Start a new timed practice attempt". Choosing the
  item writes nothing; only the start does, and it covers that one attempt. The
  review and recommendation starts are always untimed.

## What is recorded

No background process runs. The journal already stamps every event, so:

- timer start: the `attempt_started` timestamp, with `timed` and the optional
  `limit_minutes` in that event;
- time to the first passing run: the first `test_run` with status `passed`;
- time to finish: the `attempt_finished` timestamp.

Elapsed times are worked out when you ask. A finished attempt's times are fixed. An
open attempt shows time so far, measured against the clock at that moment.

## Viewing it

```text
uv run --locked practice attempt time ATTEMPT_ID
```

This prints the elapsed time at the first pass and at finish, and whether each is
within or over the limit, in a section headed "Timing (evidence only, separate from
explanation feedback and test results)". `practice notes` repeats that section for
timed attempts, apart from the explanation assessments. An untimed attempt says so.
Tutor requests and `practice tutor start` name timing only for an attempt that was
started timed.

## What timing never touches

Explanation scores, whether an attempt counts as complete, review ladder rungs and
due dates, and recommendations are computed without reading `timed` or
`limit_minutes`. Tests build the same history with and without timing (including a
pass that badly misses the limit) and assert identical statuses, scores, review
schedule and recommendation.
