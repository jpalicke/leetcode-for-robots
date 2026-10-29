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
```

Put `choose N` before the flags. Every menu prints the exact command to use next.
`practice search sum of` also works without quotes.

Main menu: resume your active attempt; browse and select a problem; progress and
notes; reviews; then recommendations, study and timed practice. The last three are
listed as "Not available yet." and do nothing. They are wired in later by #19, #39,
#40 and #41. Timed practice is never offered as runnable.

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
