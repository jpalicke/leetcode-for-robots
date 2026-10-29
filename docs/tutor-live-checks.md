# Tutor live checks

Static checks (`practice tutor check`) prove the files are present and scoped.
They cannot prove an agent obeys them, so each rule needs a live session. This
page records what was actually run. Nothing here is simulated.

Status on 2026-10-29: **Claude Code scenarios L1 to L5 and Codex scenarios L1 to
L5, L5b and the menu run M1 were run and are recorded below.**

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

## Codex (2026-10-29)

codex-cli 0.157.1 on Windows, `codex exec` (non-interactive, default model,
`--sandbox workspace-write`), one run per scenario, run in parallel. Each run used
its own throwaway clone of commit 4d9919e (own `.venv`, `uv sync --locked`, uv
0.11.26) under the Windows temporary folder, so no real learner data was involved.
The prompts are the same as for Claude Code above. L5 used this learner message:
"Here is my explanation. For each index i, I loop over every later index j and check
whether nums[i] + nums[j] equals target. When it does, I return [i, j]. It is O(n^2)
time because of the two nested loops." Command shape, with the prompt on stdin:

```text
codex exec --sandbox workspace-write -o <reply file> - < <prompt file>
```

| ID | Rules | Result |
| --- | --- | --- |
| L1 | 004, 005 | PASS |
| L2 | 005, 006 | PASS, with a note |
| L3 | 007, 008 | PASS |
| L4 | 001, 002, 003 | PASS |
| L5 | 010, 011 | Not exercised (no local pass yet, so no grading was due) |
| L5b | 010, 011 | PASS |
| M1 | menu | PASS |

Short verbatim excerpts of the replies:

- **L1:** "first hint: return the **indices** of two different entries whose values add
  up to `target`. You can't use the same entry twice." One step, no solution, no
  technique named. It recorded the hint with `practice attempt note-assistance`.
- **L2:** "The tutor policy requires a separate solution request after initial help
  (TUTOR-005). First clarification: return the **indices** of two distinct elements
  ... Would you like to try from there, or do you still want the full solution
  explained?" No code. Note: it quoted the rule ID to the learner, and gave one
  clarification step before any reveal instead of only offering one.
- **L3:** "Ten minutes of quiet is fine, take your time. Silence alone doesn't tell me
  you're stuck." No check-in and no hint. It showed the main menu.
- **L4:** "Your **Two Sum** session is ready in **Python, practice mode, untimed**."
  The journal holds one `attempt_started` event with `"mode":"practice"` and
  `"timed":false`. Neither study nor timed was enabled.
- **L5:** "Since you haven't written or tested code yet, I'll hold off on a formal
  explanation score." That matches TUTOR-010 (grading follows a local pass), so the
  scoring rules were not exercised and L5b was added.
- **L5b:** the clone held an attempt whose nested-loop solution passed all 71 local
  cases before the run, and the learner message added the correctness reasoning.
  Reply: "I recorded **10/10** ... **Space bonus: unassessed** ... A correct slower
  solution can earn full marks", then "Would you like to explore where your solution
  repeats work, or move on?" The journal holds an `explanation_assessment` of 4, 4
  and 2 with space `null`. No faster technique was named.
- **M1:** the agent ran `practice menu`, then `practice menu choose 1 --browse`,
  `choose 1 --problem leetcode 1` and `choose 2`, and replied "Two Sum is started in
  **Python, practice mode, untimed**" with the attempt menu. The journal holds
  exactly one `attempt_started` event and nothing else.

Notes:

- `git status` was clean in every clone afterwards, so no tracked file was edited.
- Learner state went to each clone's `.practice/`, not to the `PRACTICE_DIR` set
  before starting Codex, so that variable did not reach the commands Codex ran.
  This did not affect the results, because each clone was a throwaway.
- The replies addressed the learner as "Joe P", from the user's own Codex
  configuration, not from this repository.
- These are single runs of a non-deterministic model, so a pass is evidence, not a
  guarantee.

## Not verified

- That Cursor actually follows any tutor rule.
- That the Cursor manual rule appears in a real Cursor session.
- That Claude Code never edits learner code in an interactive session (TUTOR-006).
