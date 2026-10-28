# Learner history

Private attempts and a resumable history live under `.practice/`, which Git
ignores (`git check-ignore .practice` confirms it). A clean clone never needs the
directory; read-only commands such as `practice progress` do not create it.

The location is `--practice-dir PATH`, else `$PRACTICE_DIR`, else `.practice/` in
the repository.

## Layout

```text
.practice/
  journal.jsonl            the one source of truth
  journal.jsonl.lock       lock file for appenders
  attempts/<platform>-<problem>/<attempt-id>/solution.py
```

`practice attempt start` always creates a new attempt directory with an exclusive
file create. Earlier attempts are never read, printed, overwritten or copied, so a
retry is a fresh blank start. Timing is chosen per attempt with `--timed` and is
never carried forward.

## Journal

One complete JSON object per line, UTF-8, ASCII-escaped. Every record has
`schema_version`, `event_id`, `at` (UTC), `type` and, for attempt events,
`attempt_id`.

Appending takes an OS lock (`msvcrt.locking` on Windows, `fcntl.flock` elsewhere)
on the separate lock file, writes the whole line with one write, then flushes and
fsyncs. The OS drops the lock if its holder dies. Concurrent writers from real
processes are tested.

Reading never rewrites or discards anything. A malformed line, or a final line
without a newline (an interrupted write), is reported on stderr as
`journal.jsonl line N: ...` and the rest of the journal is still used. If the file
does not end in a newline, the next append starts on a fresh line, so a torn tail
stays one reportable bad line and never corrupts a later record.

## Events

| type | meaning |
| --- | --- |
| `attempt_started` | platform, problem, title, language, mode, timed, code path, starter source and hash |
| `test_run` | outcome, message, `code_sha256`, `suite_sha256`, suite version, per-case outcomes |
| `assistance` | delivered help only: `hint` (level 0 to 3), `reveal`, `concept`, optional summary |
| `platform_verdict` | `accepted`, `rejected` or `not_submitted`, plus source and date, recorded separately |
| `attempt_finished` | closes the attempt for resume; code and history stay |

Unknown event types are ignored so newer journals still read.

## Derived status

Status is computed fresh from the journal plus the current hash of the attempt
file:

- in progress: no passing run on the current code
- passed locally: the latest run on the current code passed
- stale after edit: a run passed on other code, or the file is gone; the old
  evidence stays in the journal and in `practice notes`

Reverting the file to passing code makes the pass current again. A platform
verdict never changes local status, and acceptance is never inferred. Problem
status ranks passed over stale over in progress across its attempts.

## Commands and exit codes

`attempt start|resume|list|test|note-assistance|verdict|finish`, `progress`,
`notes`. Attempt ids may be shortened to a unique prefix. Exit codes: 0 ok,
1 nothing to resume or the tested attempt did not pass, 2 usage error or unknown
or ambiguous attempt, 3 invalid catalog, package or journal.

Out of scope here: explanation assessment, review scheduling, recommendations
and paste-ready requests.
