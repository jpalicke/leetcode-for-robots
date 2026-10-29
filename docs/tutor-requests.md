# Tutor requests

`practice request` prepares a paste-ready block of text for an existing
coding-agent tutor chat. It is what a menu action such as "request a hint" produces
for conversational help. It never launches an agent, never sends anything and never
uses the network.

```text
uv run --locked practice request ATTEMPT_ID --action ACTION
    [--mode practice|study] [--reveal LEVEL|solution] [--package DIR]
```

`ATTEMPT_ID` is an exact attempt id or a unique prefix. The request is printed to
stdout and also saved as `.practice/requests/<attempt-id>-<n>-<action>.md` (under
`PRACTICE_DIR` or `--practice-dir` when those are set). `.practice/` is Git-ignored
and `practice tutor check` verifies that. A status line goes to stderr, so stdout
is exactly the text to paste.

## Actions

| Action | Asks the tutor to | Reveal option |
| --- | --- | --- |
| `hint` | give one gradual hint step | optional level `0` to `3` |
| `explain-solution` | explain the full solution | required: `--reveal solution` |
| `review-my-code` | review the current code with questions | none |
| `explain-my-approach` | start an explanation assessment conversation | none |
| `stuck` | open a gentle check-in; grants no hint | none |
| `concept-refresher` | ask which concept, then refresh it | none |

- Mode is `practice` unless `--mode study` is given for that request.
- Timing is `untimed` unless the attempt was started with `--timed`. It is read from
  that attempt only, shown as evidence, and never carried to another attempt.
- A plain `hint` request asks for the level after the highest hint recorded in the
  journal (level 0 when none). `--reveal N` asks for level `N` instead. Levels
  come from the package's `hints/index.json`; a level it does not list is refused,
  and so is a plain request once every level has been recorded as given.
- `explain-solution` is refused without `--reveal solution`. The reveal covers the
  active attempt only. `--reveal` is refused for actions it does not apply to.

## What a request holds

Content is selected by class first, and only then is context added. The classes and
their spoiler flags are read from `src/practice/classification.py` and the
package's `readiness.json` and `hints/index.json`; nothing is copied.

- Always: platform, problem id and title, attempt id, mode, timing, action, the
  permitted reveal scope, and the instruction to follow `tutor/TUTOR.md`.
- Open content is pasted: the problem statement summary.
- A spoiler that the request permits is named by path, never pasted: the one
  permitted hint file, or (for a solution reveal) the package notes.
- For actions that need it (`hint`, `review-my-code`, `explain-my-approach`,
  `stuck`), the path of the learner's current code and its local status. The code
  itself is not pasted.
- Withheld, by class name: every other spoiler class, other hint levels, other
  attempts, `references/` and the rest of `.practice/`.
- A closing instruction to run `practice attempt note-assistance` for any hint or
  reveal the agent actually gives.

## Preparing is not delivering

Generating a request writes only the request file. It appends nothing to the
journal, so no hint or reveal is recorded as delivered (TUTOR-016). The journal is
read, never written, and tests assert it is byte-identical before and after.

## When a request cannot be prepared

These cases exit nonzero with a message on stderr, print nothing on stdout and
write no file: unknown or ambiguous attempt, finished attempt, a package that is
missing, has no test suite, or lists blockers in `readiness.json`, an unsupported
action, an unknown mode, a reveal that is not classified for the problem, and a
reveal that does not fit the action.
