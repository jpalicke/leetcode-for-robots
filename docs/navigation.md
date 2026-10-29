# Navigation: the numbered menu and the terminal menu

Two front ends share one menu core (`src/practice/menu.py`). The core derives the
current state and the menu items from the journal and the exercise packages. Each
item has an id, a label, an available flag, and a reason when it is unavailable.
Actions run the same CLI commands you can type yourself, so the menus, the
terminal menu and the plain commands always agree and write the same journal.

## Numbered menu (works in any chat)

It is stateless and plain text. The screen is spelled in flags.

```text
practice menu                                  main menu
practice menu choose N                         run item N of the main menu
practice menu --browse [WORDS]                 list packaged problems, or search the catalog
practice menu choose N --browse [WORDS]
practice menu choose N --problem PLATFORM ID   a problem's menu (start or resume)
practice menu choose N --attempt ID            an attempt's menu
practice menu choose N --attempt ID --confirm-reveal
practice menu choose N --reviews               the due reviews: start or resume one
practice menu choose N --recommend             the recommendation: start a pick
practice menu --browse --timed                  the problem list, opted in to one timed start
practice menu --problem PLATFORM ID --timed     a problem's menu with the timed start first
```

Put `choose N` before the flags. Every menu prints the exact command to use next.
`practice search sum of` also works without quotes.

Main menu: resume your active attempt; browse and select a problem; progress and
notes; reviews; recommendation; study; then timed practice. Study is listed as
"Not available yet." and does nothing (it is wired in later by #40). Timed practice
is real and opt-in: choosing it opens the problem list in timed mode, and a problem's
menu then offers "Start a new timed practice attempt" first. That choice covers the
one attempt you start. It writes nothing until you start, nothing is remembered, and
the next start from any menu is untimed. See `docs/timed-practice.md`.

Recommendation: choosing it opens a screen that shows the pick, why, and the
evidence, then offers items to start the recommended problem (or resume or review it),
start an alternative, browse for another problem, or go back. It uses the same core as
`practice recommend` (see `docs/recommendations.md`) and writes nothing until you start
something. `practice menu --recommend` prints the screen in the numbered menu.

Reviews: the main menu notes how many reviews are due. Choosing Reviews opens the
reviews screen, which lists upcoming reviews for information and offers one item per
due review, to start it or, if a review attempt is already open, to resume it. These
run `practice review start` and `practice attempt resume`, so they follow the rules in
`docs/spaced-review.md`. The screen never shows earlier solution code or a technique.

Attempt menu: run tests; request a hint; request an explanation conversation about
your approach; request the full solution explanation; progress and notes; main menu.
Hints and explanations only prepare a paste-ready request (see the request command).
They do not record help as delivered. The solution explanation is an explicit
reveal and needs `--confirm-reveal`.

A problem whose package is missing or not ready (failing readiness, only a stub, or
pending) is listed as pending. It can never be started or run, and choosing it says
so and changes nothing.

Exit codes: 0 done, 1 refused or tests did not pass, 2 usage, 3 invalid input.

## Terminal menu (needs a real terminal)

`practice tui` shows the same menus with arrow-key selection (type a number, then
Enter, also works). Ctrl-C leaves. If stdin or stdout is not a terminal it exits
with code 2 and points to `practice menu`, instead of waiting for keys.

## How these are tested

Unit tests cover the core. Integration tests compare the journals written through
the menu and through the plain commands, and drive `run_tui` with the library's pipe
input. End-to-end tests run the numbered flow on Two Sum as a subprocess and, on
POSIX only, `practice tui` in a real pseudo-terminal.
