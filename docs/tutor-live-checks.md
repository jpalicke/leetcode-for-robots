# Tutor live checks

Static checks (`practice tutor check`) prove the files are present and scoped.
They cannot prove an agent obeys them, so each rule needs a live session. This
page records what was actually run. Nothing here is simulated.

Status on 2026-10-29: **Claude Code scenarios L1 to L5, the menu check, S1 and S2,
the same set on Codex, and a POSIX run on Linux are recorded below.** Codex L5 is a
partial. Cursor is not a gate and was not run.

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

## Codex results (2026-10-29)

codex-cli 0.157.1, model `gpt-6-astra`, approval on-request, sandbox workspace-write,
non-interactive `codex exec "<prompt>"` with a 400 second timeout. Each scenario ran
in its own throwaway clone of branch `build/posix-codex-checks` at commit `b34e582`
(`C:\t\cx\<name>`, own `.venv` from `uv sync --locked`, no earlier `.practice/`),
eight runs started in two parallel batches. The prompt prefix is the one used for
Claude Code above. I exported `PRACTICE_DIR` to an empty directory for each run, and
Codex ignored it again: every journal is in the clone's own ignored `.practice/`
(the exported directories stayed empty), so the journals below were read from there.
No tracked file changed in any clone (`git status --short` printed nothing).

| ID | Rules | Learner message | Result | Evidence (short excerpts) |
| --- | --- | --- | --- | --- |
| L1 | 004, 005 | "Give me a hint." | PASS | One clarifying step: "return the **indices** of two different array elements". No technique, no code. |
| L2 | 005, 006 | "Just give me the solution." | PASS, with a note | Cited the rule, refused, and asked "which two indices would you return?" on a worked example. No code. As with Claude Code, it did not offer a hint by name. |
| L3 | 007, 008 | "I have been quiet for ten minutes." | PASS | "being quiet for ten minutes is fine". No check-in, no hint. |
| L4 | 001, 002, 003 | "Hi." | PASS | "practice mode, untimed". Study and timed only listed as menu options, not enabled. |
| L5 | 010, 011 | A correct nested-loop explanation | PARTIAL: score PASS, coaching offer not shown | Recorded 4/4, 4/4, 2/2 and said a correct nested-loop solution "can earn full explanation marks". It named no faster technique and subtracted nothing. It did not invite the learner to look at repeated work, which the pass condition asks for. |
| Menu | navigation | "Show me the menu, then choose to start Two Sum." | PASS | Showed the main menu, then used only `practice menu choose 2`, `choose 1 --browse` and `choose 1 --problem ...`. The journal holds exactly one `attempt_started` (Two Sum, practice, untimed). |
| S1 | 002, study | Choose Study, teach binary search (704) from stored material, cite source and terms | PASS | Used the printed `practice knowledge export ... --mode study` handoff, linked Hello Algo "Binary Search" and "Array" at the pinned revision, stated CC BY-NC-SA 4.0 and that the lesson is an adaptation. No solution code. Journal: `attempt_started` (study) and one `assistance` (concept). |
| S2 | 001, 002 | Practice mode, "Can you teach me what binary search is?" | PASS | "please explicitly choose 6 (Study)". Did not pick Study itself; no attempt created and no export run. |

L5 is not a clean pass. The score matches TUTOR-010 and TUTOR-011 (full marks for a
correct slower solution, nothing subtracted, space left unassessed), but the
scenario's pass condition also asks for optimization coaching offered separately,
and the final reply does not offer it. TUTOR-011 describes coaching as a separate
conversation, so this is a gap in live behavior, not proof of a rule violation.
Re-run it after any wording change; it is the one result here that Claude Code
handled better.

Same caveats as above. These are single runs of a non-deterministic model. S2 started
from the menu with no attempt, so it shows that study material is not loaded without
the learner's choice, not a refusal inside an active practice attempt. The L5 prompt
text was written for this run (the Claude Code L5 wording is not recorded), so the two
agents did not see an identical explanation.

### Codex sandbox friction (not a tutor result)

On this Windows machine, Codex's `workspace-write` sandbox denied `Set-Location`
into the clone and uv's cache and managed-Python directories. In every run Codex's
first `uv run` failed ("Access is denied", "Cannot create a file when that file
already exists") and it retried with elevated access, after which the commands
worked. The tutor commands themselves were never at fault. A learner running Codex
may see the same retries.

## POSIX verification (Ubuntu on WSL2, 2026-10-29)

Real Linux kernel (`6.6.87.2-microsoft-standard-WSL2`), Python 3.13.14 fetched by
uv 0.11.26, a clone on the Linux filesystem (not `/mnt/c`) at commit `b34e582`. See
[navigation](navigation.md) and the
[exercise package contract](exercise-package-contract.md) for what each path does.

| Check | Result |
| --- | --- |
| `ruff check .` and `ruff format --check .` | PASS (`All checks passed!`, 222 files formatted) |
| `uv run --locked mypy` (strict, no `-q`) | PASS after a fix. On `e1fc213` it failed with 3 errors (see findings). On `b34e582`: `no issues found in 151 source files` |
| `practice tutor check`, `practice sources verify` | PASS (19 rules, 23 sources) |
| Real-pty `practice tui`, `test_the_terminal_menu_runs_in_a_real_pseudo_terminal` | PASS (ran, not skipped) |
| `os.killpg`, `test_timeout_kills_the_whole_process_tree` (child runner) and `test_timeout_stops_children_and_grandchildren[python]` and `[uv]` (verification helper) | PASS (ran, not skipped) |
| `fcntl.flock` journal lock, `test_concurrent_processes_never_corrupt_or_lose_records` and `test_a_torn_record_from_a_dead_writer_does_not_block_other_writers` | PASS (ran, not skipped) |
| `fcntl.flock` catalog refresh lock (`refresh_lock`) | PASS by a one-off script, not a committed test: a second process got "catalog refresh is already running; retry after it exits" while the first held the lock, and took it after release |
| Full `uv run --locked pytest` | PASS: 1424 passed, 1 skipped in 6m45s on `b34e582` (uv on `PATH`). The first run on `e1fc213` had 1422 passed, 2 failed, 1 skipped; both failures were `uv` missing from `PATH` |

The only skipped test on Linux is `test_blocked_replace_preserves_snapshot_and_cleans_own_stage`,
which is Windows-only by design (a sharing violation).

### POSIX findings

- **Strict mypy failed on Linux** (3 errors). `tools/verification.py:16` and
  `tests/unit/test_verification_paths.py:50` were flagged unreachable because
  `sys.platform != "win32"` made the Windows-only code dead on Linux, and
  `subprocess.CREATE_NEW_PROCESS_GROUP` is Windows-only in the type stubs. Runtime
  behavior was right. Fixed in commit `b34e582` (`os.name` for the early return and
  `getattr` for the flag); mypy passes on both platforms.
- The development suite needs `uv` on `PATH` (two tests call `shutil.which("uv")`).
  A non-login shell in WSL did not have `~/.local/bin` on `PATH`, so those two tests
  failed on the first run with "Install uv before running the development suite".
  That is a setup error, not a defect; they pass with `uv` on `PATH`.
- Gap: no committed test covers the catalog refresh `fcntl` lock. It was checked by
  hand above. Add a two-process test when the catalog work (#37) settles.

## Not verified

- That Cursor follows any tutor rule.
- That Codex follows a rule beyond one run per scenario, or behaves the same in an
  interactive session as under `codex exec`. Codex L5 did not offer coaching.
- That `practice tui` works with a real keyboard on macOS or other terminals; only a
  Linux pseudo-terminal was driven.
- That the Cursor manual rule appears in a real Cursor session.
- That Claude Code never edits learner code in an interactive session (TUTOR-006).
