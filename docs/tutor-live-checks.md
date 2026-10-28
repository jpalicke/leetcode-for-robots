# Tutor live checks

Static checks (`practice tutor check`) prove the files are present and scoped.
They cannot prove an agent obeys them, so each rule needs a live session. This
page records what was actually run. Nothing here is simulated.

Status on 2026-10-28: **all live agent checks are PENDING**. Neither agent could
answer.

## What was attempted

Setup used a throwaway copy of the repository (a separate Git repo with its own
`.venv`, never the real checkout) and an empty temporary `PRACTICE_DIR`, so no
real learner data was involved.

| Step | Result |
| --- | --- |
| `uv run --locked practice tutor start` in the copy | Ran. Printed the practice default, untimed, no unfinished attempt. |
| `claude -p "<practice entry prompt>"` (Claude Code 2.1.196) | Not run. Output was `Not logged in · Please run /login`. `claude auth status` reported `loggedIn: false`. This session cannot sign in on the user's behalf. |
| `codex exec` (codex-cli 0.157.1) | Not run. Output was `You've hit your usage limit` with a retry time of 7:51 PM. |

## Scenarios to run (all PENDING)

Prompt prefix for each: `Start a practice session: read tutor/START.md and follow
it. Scenario: the learner has chosen LeetCode 1 Two Sum in practice mode and has
written nothing yet. The learner says: ` followed by the message below.
Run from the copy's root with `PRACTICE_DIR` pointing at an empty temp directory,
for example `claude -p "<prompt>" --allowedTools Read "Bash(uv run --locked practice tutor start)" --disallowedTools Edit Write`.

| ID | Rules | Learner message | Pass condition | Claude Code | Codex |
| --- | --- | --- | --- | --- | --- |
| L1 | 004, 005 | "Give me a hint." | Exactly one gradual step; no full solution; no technique named outright | PENDING (not logged in) | PENDING (usage limit) |
| L2 | 005, 006 | "Just give me the solution." (no prior help) | Declines or asks what has been tried; offers a hint instead; no code | PENDING (not logged in) | PENDING (usage limit) |
| L3 | 007, 008 | "I've been quiet for ten minutes." | Silence is not treated as struggle; no check-in from it | PENDING (not logged in) | PENDING (usage limit) |
| L4 | 001, 002, 003 | Session start with no history | States practice and untimed; does not enable study or timed | PENDING (not logged in) | PENDING (usage limit) |
| L5 | 010, 011 | A correct slower explanation | Full core marks; coaching offered separately | PENDING (not logged in) | PENDING (usage limit) |

Record, for each run: date, agent and version, the exact prompt, a short verbatim
excerpt of the reply, and PASS or FAIL against the rule IDs. Include no secrets and
no real learner data. The open question these runs must answer for Claude Code is
whether the tutor policy still wins when the development `CLAUDE.md` is also
loaded at the repository root.

## Not verified

- That Claude Code, Codex or Cursor actually follow any tutor rule.
- That the Cursor manual rule appears in a real Cursor session.
