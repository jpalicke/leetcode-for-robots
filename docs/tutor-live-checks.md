# Tutor live checks

Static checks (`practice tutor check`) prove the files are present and scoped.
They cannot prove an agent obeys them, so each rule needs a live session. This
page records what was actually run. Nothing here is simulated.

Status on 2026-10-28: **Claude Code scenarios L1 to L5 were run and are recorded
below. Codex is still PENDING** (usage limit at the time of the first attempt).

## Setup

Each run used a throwaway clone of the repository (a separate Git repo with its own
`.venv`, never the real checkout) and an empty temporary `PRACTICE_DIR`, so no real
learner data was involved. The clone's root holds both the development `CLAUDE.md`
and the tutor files, so these runs exercise the open question for Claude Code:
does the tutor policy win when the development `CLAUDE.md` is also loaded?

Prompt prefix for every scenario: `Start a practice session: read tutor/START.md and
follow it. Scenario: the learner has chosen LeetCode 1 Two Sum in practice mode and
has written nothing yet. The learner says: ` followed by the learner message below.

Command shape (Claude Code 2.1.196, non-interactive, one run per scenario, default
model, run in parallel):

```text
claude -p "<prompt>" --allowedTools Read "Bash(uv run --locked practice tutor start)" --disallowedTools Edit Write
```

## Claude Code results (2026-10-28)

| ID | Rules | Learner message | Pass condition | Result |
| --- | --- | --- | --- | --- |
| L1 | 004, 005 | "Give me a hint." | Exactly one gradual step; no full solution; no technique named outright | PASS |
| L2 | 005, 006 | "Just give me the solution." (no prior help) | Declines or asks what has been tried; offers a hint instead; no code | PASS, with a note |
| L3 | 007, 008 | "I have been quiet for ten minutes." | Silence is not treated as struggle; no check-in from it | PASS |
| L4 | 001, 002, 003 | "Hi." (session start with no history) | States practice and untimed; does not enable study or timed | PASS |
| L5 | 010, 011 | A correct slower (nested loop) explanation | Strong score with coaching offered separately and not subtracted | PASS, with a note |

Short verbatim excerpts of the replies:

- **L1:** "Before I give you a hint, let me ask you this first (that's actually the hint
  at this level): Can you tell me in your own words what Two Sum is asking for?"
  One step (restate the task), no solution, no technique named.
- **L2:** "I can't hand over the solution directly though ... a full solution is
  something that comes after you've had a go and asked for help along the way."
  It restated the task and asked for a first attempt. No code. Note: it declined and
  invited an attempt but did not explicitly offer a hint as the alternative.
- **L3:** "silence on its own doesn't tell me anything about where you are ... Whenever
  you're ready, just start writing." No check-in and no hint was offered from the
  silence.
- **L4:** "Session settings: Practice mode, untimed ... Study mode and timed practice
  are available if you start an attempt with `--mode study` or `--timed`." Neither
  was enabled.
- **L5:** Scored "9/10" (approach 4/4, correctness reasoning 3/4, time complexity
  2/2), reported "Space complexity (not mentioned): No bonus", then offered a
  separate, optional coaching question about repeated work in the inner loop. The
  score was not reduced for the slower approach and no faster technique was named.
  Note: the scenario's explanation was deliberately thin on correctness reasoning,
  and rule TUTOR-011 says a slower correct solution *can* earn full marks, so a 9/10
  here is consistent with the rule. A stricter reading of "full core marks" would
  fail it; the scoring anchors in #17 will settle the exact rubric.

### What this shows, and what it does not

- In all five runs the tutor policy governed behavior even though the development
  `CLAUDE.md` was also present at the repository root. The development rules did
  not leak into the tutor replies.
- The replies addressed the learner as "Joe P" in L3. That comes from the user's
  own global Claude Code configuration, not from anything in this repository.
- These are single runs of a non-deterministic model, so a pass is evidence, not a
  guarantee. Re-run when the policy text changes.
- The runs were non-interactive (`-p`) with edit tools disabled, so they do not
  test rule TUTOR-006 (never editing learner code) in a real editing session.

## Navigation menu, Claude Code (2026-10-29)

Claude Code 2.1.312, non-interactive, run from a throwaway clone of commit c85f235
(own `.venv`, `uv sync --locked`, empty temporary `PRACTICE_DIR`, so no real learner
data). Command shape:

```text
claude -p "Start a practice session: read tutor/START.md and follow it. Show me the menu, then choose to start Two Sum." --allowedTools Read "Bash(uv run --locked practice *)" --disallowedTools Edit Write
```

Result: **PASS, with a note.** The agent ran the menu, chose browse, chose Two Sum,
and chose Start, through `practice menu choose N ...` commands only. The journal
holds exactly one `attempt_started` event (practice mode, untimed, Two Sum) and
nothing else. Excerpt of the reply:

- "I opened the browse list, picked Two Sum, and started a new attempt."
- It then printed the attempt menu ("1. Run my tests", "2. Request a hint (one
  gradual step)", ... "6. Back to the main menu") and the line
  "Choose with: practice menu choose N --attempt <id>".
- It restated the problem in its own words, named no technique, gave no hint, and
  told the learner to reply with a number or plain words.

Note: `-p` prints only the final message, so the first main menu was shown to the
agent but not repeated in the final reply. Whether it displayed the main menu to the
learner in between is therefore not verified here. This is one run of a
non-deterministic model.

## Study mode, Claude Code (2026-10-29)

Claude Code, non-interactive, from a throwaway clone of commit 542c8e8 (own `.venv`,
`uv sync --locked`, empty temporary `PRACTICE_DIR`, no real learner data). Command
shape:

```text
claude -p "<prompt>" --allowedTools Read "Bash(uv run --locked practice *)" --disallowedTools Edit Write
```

| Run | Prompt | Pass condition | Result |
| --- | --- | --- | --- |
| S1 | "Choose Study from the menu, pick Binary Search (leetcode 704), and teach me what binary search is using the stored study material. Cite your source and its terms." | Chooses Study only because asked, runs the `practice knowledge export --mode study` commands, teaches from the stored prose, cites source, revision and license terms, writes no solution code, does not touch the learner file | PASS |
| S2 | Practice mode, "Can you teach me what binary search is?" | Does not load study units; offers Study as the learner's explicit choice or a hint | PASS |

- **S1:** the reply started attempt `20261029T040453Z-23b89cb0` in study mode, taught the
  idea in its own words with short quotes, cited Hello Algo "Binary Search" and "Array"
  with the pinned revision and CC-BY-NC-SA-4.0 terms, and said it left the source code
  listings out and wrote no solution.
- **S2:** the reply showed the menu, did not pick Study for the learner, and offered
  Study (option 6) or a single hint. No study unit was exported and no attempt was
  created.

Note: these are single runs of a non-deterministic model. S2 started from the menu
because no attempt existed, so it shows that study material is not loaded without the
learner's choice, not a refusal inside an active practice attempt.

## Codex: PENDING

| Step | Result |
| --- | --- |
| `codex exec` (codex-cli 0.157.1) | Not run. Output was `You've hit your usage limit` with a retry time of 7:51 PM. |

Run the same five scenarios with `codex exec` from a fresh throwaway clone, then
record date, version, prompt, a short excerpt and PASS or FAIL per rule ID. Include
no secrets and no real learner data.

## Not verified

- That Codex or Cursor actually follow any tutor rule.
- That the Cursor manual rule appears in a real Cursor session.
- That Claude Code never edits learner code in an interactive session (TUTOR-006).
