# Tutor contract

Practice sessions are tutored by a coding agent. Development work on this
repository is done by coding agents too. The two jobs need different
instructions, so they live in different files and are never mixed.

| File | Audience | Loaded by |
| --- | --- | --- |
| `CLAUDE.md` | Agents developing this repository | Claude Code, automatically |
| `tutor/TUTOR.md` | Practice sessions only | Only when a session is pointed at it |
| `tutor/START.md` | The practice entry point | A learner's first prompt names it |
| `.cursor/rules/practice-tutor.mdc` | Optional Cursor pointer | Only by an `@practice-tutor` mention |

## Location decision

The issue's layout decision supersedes the criteria that name a root
`AGENTS.md`. A root `AGENTS.md` is read automatically by Codex and, when no
`CLAUDE.md` exists, by Claude Code, so a tutor policy there would load into every
development session. The policy therefore lives in `tutor/TUTOR.md`, a name no
agent discovers on its own, and `tutor/START.md` is the explicit entry point.
`CLAUDE.md` mentions the tutor files in backticks (so it is not an import) and
carries no tutor behavior. `practice tutor check` enforces this, and also fails if
a root `AGENTS.md` ever carries tutor rules.

Known limit: Claude Code started at the repository root also loads `CLAUDE.md`.
That file only says development rules apply to development, so it does not tell
the agent to tutor, but a practice session in Claude Code does see development
rules as well. Live checks must show the tutor policy still wins (see
[tutor live checks](tutor-live-checks.md)). Codex does not read `CLAUDE.md`
(see below), so a Codex practice session sees only what `START.md` points at,
plus any `AGENTS.md` files, of which this repository has none.

## Official conventions (retrieved 2026-10-28)

### Claude Code

Source: https://code.claude.com/docs/en/memory

- `./CLAUDE.md` or `./.claude/CLAUDE.md` is loaded at launch, together with
  those in directories above the working directory. Subdirectory files load on
  demand when Claude reads a file there. Content is concatenated, not overridden.
- `@path` imports are expanded; code spans and fenced blocks are skipped, so a
  path in backticks is literal and not imported. This is why `CLAUDE.md` writes
  `tutor/TUTOR.md` in backticks.
- `AGENTS.md` is read only when no `CLAUDE.md` or `CLAUDE.local.md` exists in
  the working directory or above (requires Claude Code v2.1.277 or later).
- CLAUDE.md is context, not enforced configuration. Blocking an action needs a
  hook. This is why the policy is backed by live checks and not only by static
  ones.
- Confirm what loaded with `/memory`, which lists loaded instruction files.
  The page also documents an `InstructionsLoaded` hook (https://code.claude.com/docs/en/hooks).
  Its exact input fields were not confirmed here because the fetched page was
  truncated, so no check relies on it.

Setup check: start `claude` in the repository root, run `/memory`, and confirm
`CLAUDE.md` is listed and `tutor/TUTOR.md` is not. Then type `Read tutor/START.md
and follow it` and confirm the reply states the session settings printed by
`practice tutor start`.

### Codex

Source: https://developers.openai.com/codex/guides/agents-md (redirects to
https://learn.chatgpt.com/docs/agent-configuration/agents-md)

- Codex reads `AGENTS.override.md` or `AGENTS.md` from its home directory, then
  one file per directory from the project root down to the working directory,
  plus names in `project_doc_fallback_filenames`. Total size is capped by
  `project_doc_max_bytes` (32 KiB by default).
- The page does not mention `CLAUDE.md`. Under the documented behavior Codex does
  not read it, unless `CLAUDE.md` is added to the fallback names in the user's
  config. The page does not confirm that either.
- Verify with `codex --ask-for-approval never "Summarize the current instructions."`
  from the repository root. It should report no tutor policy. For a practice
  session use `codex exec` or the interactive prompt:
  `Read tutor/START.md and follow it.`

### Cursor (optional)

Source: https://cursor.com/docs/rules

- Project rules live in `.cursor/rules/` as `.mdc` files. Plain `.md` files in
  that folder are ignored.
- With `alwaysApply: false` and neither `globs` nor `description`, a rule is
  included only when @-mentioned (the "Apply Manually" type).
- `@file` references inside a rule are not inlined, so the rule says to read the
  policy and carries none of it.
- The page documents no indicator that a rule applied. Customize shows each
  rule and its status; the check is to confirm the rule is listed as manual.
- Cursor also reads `AGENTS.md`, which is another reason there is none.

The repository works fully without Cursor. Delete `.cursor/` and
`practice tutor check` still passes.

## Starting a practice session

1. Open a Codex or Claude Code session in the repository root.
2. Say: `Read tutor/START.md and follow it.` (Cursor: `@practice-tutor`.)
3. The agent reads `tutor/TUTOR.md`, runs `uv run --locked practice tutor start`
   and reports the mode, the timing and the active attempt.

`practice tutor start` prints only settings, never code, notes or assistance
summaries. Everything else in `.practice/` stays unread until the learner agrees.

## Rule IDs

`TUTOR-001` to `TUTOR-019`. Tests and live checks cite them.

| ID | Rule |
| --- | --- |
| 001 | Practice is the default and untimed |
| 002 | Study mode needs explicit selection |
| 003 | Timed practice needs explicit opt-in |
| 004 | A generic hint grants exactly one gradual step |
| 005 | A full solution needs a separate explicit request |
| 006 | The learner types the solution; edits need a separate request |
| 007 | Check-ins come only from observable struggle |
| 008 | Silence is not struggle; no background or browser monitoring |
| 009 | Local completion, acceptance, explanation and coaching are separate |
| 010 | Explanation: core 10 (4+4+2), separate space bonus up to 1 |
| 011 | A slower correct solution can score full marks |
| 012 | Alternatives are judged on merit |
| 013 | Reveal boundaries follow the content class list |
| 014 | Learner-private classes are spoilers |
| 015 | A refresher that hints counts as a hint (ask first) |
| 016 | Recording assistance is deliberate |
| 017 | `.practice/` stays local and ignored |
| 018 | Preserved upstream is untouched; provenance is honest |
| 019 | A session changes no repository file |

## What `practice tutor check` verifies

- `tutor/TUTOR.md` exists, defines every required ID once, and no unknown ID.
- Its content class list matches `src/practice/classification.py`
  (`practice tutor classes` prints the block to paste).
- `tutor/START.md` points at the policy.
- `CLAUDE.md` exists, does not import the policy, names no rule ID and copies
  no policy lines; a root `AGENTS.md`, if present, carries none either.
- Any Cursor rule is manual (no `alwaysApply: true`, `globs` or `description`),
  points at the policy and carries no policy text.
- No tutor text names a technique behind the starter problems.
- `git check-ignore` confirms `.practice` paths are ignored by a `.gitignore`
  (not only `.git/info/exclude`) and `git ls-files` shows nothing tracked there.

Exit codes: 0 contract holds, 3 problems found (all printed to stderr).
