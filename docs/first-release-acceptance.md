# First-release acceptance

This page is the evidence for issue #42, "Verify the first release end to end". It
records a clean-clone run of the fifteen acceptance scenarios from
[the specification](specification.md) (section 13). Every row says how it was
exercised, shows a short excerpt of what actually happened, and links the code, test
or document that covers it. Nothing here is simulated. A scenario that could not be
run in full is PENDING, and anything that went wrong is FAIL. Neither is ever PASS.

Run date: 2026-10-29 (UTC clock of the machine). Platform: Windows 11, Python 3.13,
uv, Claude Code 2.1.312, codex-cli 0.157.1. Commit under test: `c9ffee3` (main after
PR #72) on branch `build/first-release-acceptance`.

The catalog refresh half of scenario 13 is PENDING, and Cursor is not a gate. See
[Pending and not verified](#pending-and-not-verified).

## 1. Clean-clone run log

The repository was cloned from the local checkout into a short path, `C:\t\accept`,
at the branch head, with no `.practice` directory. Only the documented setup in
[README.md](../README.md) and [development.md](development.md) was followed.
`TEMP` and `TMP` were set to `C:\t` for pytest, and the learner state for the
walkthrough went to a fresh directory (`C:\t\walk-pd`) through `PRACTICE_DIR`.

| Step | Command | Outcome |
| --- | --- | --- |
| Clone | `git clone --branch build/first-release-acceptance <local path> C:/t/accept` | HEAD `c9ffee3`; no `.practice`, `git status` clean |
| Install | `uv sync --locked` | exit 0, dependencies installed in about 1.5 seconds (uv cache was already warm) |
| Lint | `uv run --locked ruff check .` | `All checks passed!` |
| Format | `uv run --locked ruff format --check .` | `214 files already formatted` |
| Types | `uv run --locked mypy` (no `-q`) | `Success: no issues found in 145 source files` |
| Tutor contract | `uv run --locked practice tutor check` | `Tutor contract ok: 19 rules in tutor/TUTOR.md.` |
| Sources | `uv run --locked practice sources verify` | `23 source(s) verified`, exit 0 |
| Curriculum | `uv run --locked practice curriculum check` | `Curriculum valid.` |
| Tests | `uv run --locked pytest` with `TEMP=TMP=C:\t` | see [Final verification](#final-verification) |

After every command above and the whole walkthrough, `git status --short` in the
clone printed nothing (learner state lives outside the clone, and `.practice/` is
ignored anyway).

### Clean-clone findings

- No undocumented step was needed. The documented commands were enough.
- Cold-cache install was not tested: the uv cache was warm, so the 1.5 second sync
  says nothing about a first-ever install. The clean-checkout e2e test
  (`tests/e2e/test_clean_setup.py`) covers a locked sync that fills the cache.
- The default Windows temporary path was not exercised; the short `C:\t` path was
  used as the task required. [development.md](development.md) states that ordinary
  Windows temp paths work, and the suite has a preflight for over-long paths.
- `practice attempt start hackerrank 1` fails with `C:\t\accept\problems\hackerrank-1
  is not a directory` (exit 2), and `--language rust` is rejected by argparse as an
  invalid choice. Both are clean refusals, but the first message does not say "that
  platform is not supported". This is a usability note, not a failure.
- Codex ran its shell without the `PRACTICE_DIR` variable I had exported, so it
  wrote its attempt to `.practice/` inside the throwaway clone instead of the
  directory I intended. Claude Code inherited the variable. This only matters for
  people who rely on `PRACTICE_DIR` with Codex; `--practice-dir` on each command is
  the reliable form there. Nothing was written outside ignored paths.

## 2. Scenario checklist

Legend: PASS, PENDING (not run in full), FAIL. "Live" means a real Claude Code or
Codex session; transcripts are summarized, since `-p` and `exec` print only the
final message. Live sessions run from separate throwaway clones (`C:\t\live`) with
edit tools disabled for Claude Code. The attempt ids below come from those runs.

| # | Scenario | Status | How it was exercised | Evidence | Covered by |
| --- | --- | --- | --- | --- | --- |
| 1 | Select a problem or get a recommendation without Cursor | PASS | `practice menu`, `menu choose 2`, `menu choose 1 --browse`, `practice recommend`, `practice search "two sum"` | Menu lists six packaged problems; recommend prints "Recommended next: 1 Two Sum [easy] ... To start it: practice attempt start leetcode 1". No editor is involved. | [navigation](navigation.md), [recommendations](recommendations.md), `tests/e2e/test_practice_menu.py`, `tests/e2e/test_practice_recommend.py` |
| 2 | Complete a prepared Python exercise through both agents | PASS (Claude Code, Codex) | Claude Code: phase 1 start the attempt, phase 2 I placed `hash_map.py` in the attempt file and asked it to run my tests. Codex: same two phases with `codex exec`. | Claude Code: "your solution passed all 71 local cases ... marks the problem complete locally. It says nothing about LeetCode." Codex: "all 71 local test cases passed ... LeetCode acceptance remains unconfirmed". Both journals hold `attempt_started` and `test_run passed`. Code hash `ad0fd66a...` unchanged by both agents. The Codex run was repeated from a second fresh clone (`C:	\codex-run`, attempt `20261029T043152Z-6008cd39`) and re-checked on disk: the journal has `attempt_started` and `test_run passed`, and the attempt file hash was byte-identical before and after. | [tutor contract](tutor-contract.md), `tests/e2e/test_two_sum_learner_flow.py` |
| 3 | A small hint, not pseudocode or a full solution | PASS (Claude Code, Codex) | Claude Code: "I think my solution is too slow. Give me a hint." Codex: "Give me a hint." (L1 style). Earlier Claude Code L1, L2 recorded in [tutor live checks](tutor-live-checks.md). | Claude Code replied with one question, "What do you notice when you trace one number through your code?", and recorded a level 1 hint. Codex gave a statement clarification (return the indices, no reuse of an element) and recorded a level 0 hint. No technique named. | [tutor live checks](tutor-live-checks.md) L1, L2; TUTOR-004, TUTOR-005 in `tutor/TUTOR.md` |
| 4 | Potentially revealing refresher gets a permission check first | PASS (Claude Code) | Claude Code, "Can you give me a quick refresher on how hash maps work? Just show me whatever you think I need." | "a hash map refresher could point at a way to solve it. In practice mode that counts as a hint, so I'm checking with you before I give it. Do you want it?" It offered a technique-free syntax answer as the alternative. Codex was not run for this one. | TUTOR-015 in `tutor/TUTOR.md`; [tutor live checks](tutor-live-checks.md) |
| 5 | Tutor leaves the learner's attempt unchanged during normal help | PASS (Claude Code, Codex) | SHA-256 of the attempt file before and after: a test-and-record request, a hint request, a hash-map refresher request and an explanation-assessment request on Claude Code; a test-and-record request and a hint request on Codex. | Claude Code: hash `ad0fd66a...` before and after the test run; `6ded4dcd...` before and after the hint run, the refresher run and the explanation run. Codex: `ad0fd66a...` unchanged after test run; brute-force hash unchanged after the hint run. Claude Code's Edit and Write tools were disabled, so for Claude Code this shows the policy plus tool limits, not a model that was free to edit. Codex had no such limit and still left the file alone. | TUTOR-006, TUTOR-019; `tests/e2e/test_tutor_request_cli.py` |
| 6 | Valid alternative algorithm passes with appropriate feedback | PASS | `practice attempt test` on `leetcode_two_sum_solutions/sort_and_pointers.py` (sort plus two pointers) and `hash_map.py` | Both report `PASSED leetcode/1: all 71 cases passed`. The tutor side of "appropriate feedback" is TUTOR-012, not tested live here. | `tests/e2e/test_two_sum_learner_flow.py::test_alternate_approaches_pass_through_the_cli`, TUTOR-012 |
| 7 | Accurate O(n^2) explanation, strong score, optimization coaching offered separately | PASS | CLI: `practice attempt explain ... --approach 4 --correctness 4 --time 2 --space 1 --coaching "..."` on a nested-loop attempt. Live: Claude Code assessed a spoken-style explanation of the same loop. | CLI: "Recorded initial explanation assessment ...: 10/10 +1 bonus. Completion and local test results are unchanged." Claude Code: "10/10, plus 1 bonus", then offered a separate conversation about repeated work "that is separate from the grade and never lowers it". The journal row holds approach 4, correctness 4. | `tests/e2e/test_explanation_assessment.py::test_slow_correct_solution_earns_full_core_and_a_separate_bonus`, [tutor live checks](tutor-live-checks.md) L5 |
| 8 | Local completion recorded without inventing LeetCode acceptance | PASS | `practice progress leetcode 1` after a pass, then `practice attempt verdict --status accepted --source "..."` | After the pass: `passed locally` and `platform verdict: none recorded`. Only after the explicit `verdict` command did it say `platform verdict: accepted (2026-10-29, LeetCode submissions page (learner reported))`, with status still `passed locally`. Both agents' replies also said acceptance was not recorded. | `tests/e2e/test_attempt_history.py::test_verdict_alone_never_creates_a_local_pass`, [learner history](learner-history.md) |
| 9 | Resume an interrupted session with progress and preserved code | PASS | `practice attempt resume` and `resume leetcode 1` in new processes; hash of the code file before and after; `attempt finish` then `resume` | `Resume attempt 20261029T041803Z-5597a7fe ... Status: passed locally ... Last test run: passed`. Code hash unchanged. After `finish`: `No unfinished attempt to resume` (exit 1). | `tests/e2e/test_attempt_history.py::test_demo_start_quit_resume_test_edit_and_see_the_pass_go_stale` |
| 10 | Blank review preserves and withholds earlier code | PASS | `PRACTICE_NOW=2026-10-31T10:00:00+00:00 practice review list` then `review start leetcode 1`; `diff` of the new file against the starter | "Earlier solutions are kept on disk and are not shown. Start from the starter." The new file is byte-identical to `starter.py`; the old file's hash was unchanged; the attempt menu does not print earlier code. The `tutor start` briefing says earlier attempts are "Not printed on purpose". | `tests/e2e/test_attempt_history.py::test_blank_review_attempt_preserves_the_earlier_code`, `tests/e2e/test_practice_reviews.py`, [spaced review](spaced-review.md) |
| 11 | Ordinary session is untimed, even after timed practice | PASS | `attempt start leetcode 217 --timed --limit-minutes 20`, then `attempt start leetcode 217`, then `attempt time` on both and `tutor start` | First attempt: `practice, timed, 20 minute limit`. Next start: `practice, untimed`. `attempt time` on the second: "Untimed attempt: nothing was timed". `tutor start` printed `Timing: untimed`. | `tests/e2e/test_timed_practice.py::test_the_demo_start_timed_finish_view_time_then_start_untimed`, [timed practice](timed-practice.md) |
| 12 | Known defect caught; empty suite or unimplemented starter cannot complete | PASS | Starter tested unchanged; `off_by_one.py` and `positives_only.py` against the real package; an empty-suite copy of the Two Sum fixture (cases `[]`, in a temp folder) run with a correct solution; `stub_pass.py` | Starter: `STUB leetcode/1: incomplete: twoSum is still a stub`, exit 1. `off_by_one`: `FAILED ... 54 passed, 17 failed of 71 cases`. `positives_only`: `37 passed, 34 failed of 71`. Empty suite: `NO_SUITE ... the package has no test cases, so nothing was checked`, exit 1. `progress` stayed `in progress` throughout. | `tests/integration/test_runner.py::test_empty_suite_is_never_a_pass`, `tests/integration/test_two_sum_solutions.py` |
| 13 | Existing work intact on same-problem restart or catalog refresh | PENDING (restart half PASS) | Restart: a second `practice attempt start leetcode 1` after a finished, passing attempt. Refresh: not run. | Restart: new attempt `20261029T041903Z-dc69297f`; the earlier file's hash was identical before and after; three attempt folders coexist. Refresh: no catalog refresh command exists yet; it is being delivered in #37, so that half is PENDING. | `tests/integration/test_attempts.py::test_a_new_attempt_never_touches_earlier_code`, [learner history](learner-history.md) |
| 14 | Default export has no solutions, attempts or personal progress | PASS | `practice knowledge export leetcode 1` run with `PRACTICE_DIR` pointing at a populated journal, output saved and searched | One document, `statement_summary`, 2,640 bytes, byte-identical on a second run. Zero hits for solution text (`seen`, `hash_map`, `enumerate`, `sorted(`, `raise ValueError`), attempt ids, `attempt_started`, `passed locally`, `learner`, the learner's code hash and the practice directory path. The only hits for `accepted` and `def twoSum` are the statement's "accepted answer" and the signature stub. `--hint-level 2` adds only `hint`. | `tests/integration/test_knowledge_export.py::test_default_never_opens_excluded_bodies`, [knowledge export](knowledge-export.md) |
| 15 | Platform and language explicit in records | PASS | Journal read after the walkthrough; `attempt start leetcode 1 --language rust`; `attempt start hackerrank 1` | Every `attempt_started` event has `platform: leetcode`, `problem_id`, `language: python`, `mode`, `timed`. Test runs, assessments and verdicts attach through `attempt_id`, so outcomes are never merged across platforms or languages. Review tracks are keyed by platform, problem and language. Rust is rejected (`invalid choice: 'rust' (choose from 'python')`) and an unknown platform is refused with exit 2. | [learner history](learner-history.md), `tests/integration/test_attempts.py`, [spaced review](spaced-review.md) |

### Live session notes

- Claude Code runs: `claude -p "<prompt>" --allowedTools Read "Bash(uv run --locked practice *)" --disallowedTools Edit Write`, prompt prefix as in [tutor live checks](tutor-live-checks.md): "Start a practice session: read tutor/START.md and follow it. Scenario: ...". Each ran in `C:\t\live` with `PRACTICE_DIR=C:\t\live-pd-claude`.
- Codex evidence was confirmed from files on disk, not from Codex's own output: journal contents and SHA-256 of the attempt file before and after, in a fresh clone with no earlier `.practice/`. Codex ignored the exported `PRACTICE_DIR`, so its state is in that clone's ignored `.practice/`.
- Codex runs: `codex exec "<same style prompt>"` from `C:\t\live`. The earlier usage-limit error did not recur, so Codex is no longer PENDING for scenarios 2, 3 and 5. Codex v0.157.1 reported model `gpt-6-astra`, approval on-request, sandbox workspace-write.
- One Claude Code hint run ended with a final message that said the hint was recorded but did not state the hint ("Send me your answers"). Running the same prompt again with `--output-format stream-json` showed a proper hint. A single `-p` final message can hide what the learner would have seen, so the hint wording was confirmed from the second run, not the first.
- Claude Code's reply to the explanation request called the attempt "stale after edit", because I swapped the file after the last test run. It then said it had not read the code, which is the intended behavior. The score was assessed from the learner's words only.
- Single runs of non-deterministic models are evidence, not a guarantee. Re-run when the tutor policy changes.

## 3. Private-state and default-export checks

| Check | Command | Result |
| --- | --- | --- |
| `.practice/` is ignored | `git check-ignore -v .practice/journal.jsonl .practice/attempts/leetcode-1/x/solution.py` | Both matched by `.gitignore:13:.practice/` |
| Nothing under `.practice` is tracked | `git ls-files -- .practice \| wc -l` | `0` |
| No journal, attempt folder or `solution.py` is tracked | `git ls-files \| grep -E "(^\|/)(journal\.jsonl(\.lock)?\|attempts/\|solution\.py$)"` | no matches |
| The clone is clean after setup, checks and walkthrough | `git status --short` in `C:\t\accept` | no output |
| Learner state stays outside the repo when moved | walkthrough used `PRACTICE_DIR=C:\t\walk-pd` | journal and attempts only there |
| Read-only commands create nothing | `practice progress` against an empty directory | covered by `tests/e2e/test_attempt_history.py::test_progress_with_no_history_works_and_creates_nothing` |
| The tutor guard checks the same thing | `practice tutor check` | exit 0; `tests/integration/test_tutor_private_state.py` shows it reports a tracked or unignored `.practice` |
| Default export is learner-free | see scenario 14 | one `statement_summary` document, no solution or learner text |
| Codex and Claude Code left tracked files alone | `git status --short` in `C:\t\live` after all agent runs | no output (Codex's `.practice/` is ignored) |

## 4. Pending and not verified

- Scenario 13, catalog refresh half: no refresh command exists yet. It is tracked
  in #37. The restart half is verified above.
- Cursor: not a gate, not run. The manual rule file exists but was not exercised in a
  real Cursor session.
- Scenario 4 and the deeper L2 to L5 rules were run live on Claude Code only. Codex
  was run for scenarios 2, 3 and 5 only, one session each. Codex on the
  refresher (scenario 4), the explanation (scenario 7) and the other L-scenarios is
  not verified.
- Scenario 6 feedback wording: the tests pass for alternative algorithms, but no live
  session checked that the tutor's spoken feedback praises or compares the
  alternative appropriately.
- Scenarios 2, 3, 5 and 7 on Claude Code ran with edit tools disabled, so they do not
  prove that an agent with write access refrains from editing (TUTOR-006). The Codex
  runs had write access in a workspace-write sandbox and left the file unchanged,
  once per scenario.
- Interactive Claude Code and the terminal arrow-key menu (`practice tui`) were not
  driven by hand. The numbered menu was used through the real CLI.
- Cold-cache install, the default long Windows temp path and non-Windows platforms.
- LeetCode acceptance of any solution: the project never contacts LeetCode; the one
  `accepted` verdict above was typed by me to show the separation, and means nothing.

## Final verification

Clean clone `C:	ccept` at `c9ffee3`, `TEMP=TMP=C:	`: ruff check passed, ruff format
check passed (214 files), strict mypy passed (145 source files), `practice tutor check`,
`practice sources verify` (23 sources) and `practice curriculum check` passed, and
`uv run --locked pytest` gave **1373 passed, 1 skipped in 768 seconds**, exit 0. The
same checks on the branch that adds this page are recorded in the delivery comment on
issue #42.
