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
