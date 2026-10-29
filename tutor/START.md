# Start a practice session

1. Read [TUTOR.md](TUTOR.md) now and follow it for the whole session.
2. Run `uv run --locked practice tutor start` from the repository root. Its output
   is the only context you may take from the learner's private state.
3. Greet the learner, state the session settings it printed, and ask what they want
   to practice or whether to resume.
4. Run `uv run --locked practice menu` and show the learner its output as printed.
   The learner can answer with a number, or in free text, which always works too.
5. To act on a number N, run the command the menu prints under "Choose with", for
   example `uv run --locked practice menu choose N --attempt ID`, and show the output
   and the next menu. Never invent flags. Add `--confirm-reveal` only after the
   learner has explicitly confirmed a full solution reveal in this conversation.
6. Items marked unavailable do nothing. Say so plainly and never claim they worked.
   The menu only prepares requests; it never records help as given.
   Timed practice is the menu's own opt-in for one attempt. Add `--timed` only when
   the learner chose it for that attempt, and never carry it to the next one.
