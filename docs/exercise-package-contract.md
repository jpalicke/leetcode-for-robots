# Exercise package contract and runner

This describes what `practice run` executes and what it reports. It covers the
primitive, list and string function contracts. Node, mutation, stateful and
interactive adapters need their own future tickets; a package that asks for one
is reported as `unsupported` and never run.

## Package layout

An exercise package is a directory, for example `problems/<platform>-<id>/`:

```text
problem.json   metadata and the callable contract
tests.json     the test suite
```

Prepared packages add files the runner ignores: `starter.py`, `statement.md`,
`notes.md` (a spoiler), `hints/` with an `index.json`, and `readiness.json`. See
[exercise preparation](exercise-preparation.md).

### problem.json

```json
{
  "platform": "fixture",
  "id": "two-sum-runner-fixture",
  "title": "Two Sum",
  "language": "python",
  "callable": {
    "adapter": "function",
    "name": "two_sum",
    "parameters": ["nums", "target"]
  },
  "checker": "indices_sum_to_target",
  "allow_none": false
}
```

- `language` must be `python`. `callable.adapter` must be `function`: a top-level
  function in the learner file, called with positional JSON arguments.
- `checker` names how answers are judged (default `exact`).
- `allow_none` (default `false`): whether `None` is a legal answer. When false,
  a body of only `return None` is a stub and a `None` result is malformed.

### tests.json

```json
{
  "version": "fixture-1",
  "cases": [
    {"id": "example-1", "args": [[2, 7, 11, 15], 9], "expected": [0, 1]}
  ]
}
```

`version` is a string that changes whenever the cases change. Each case has a
unique `id`, `args` (one JSON value per parameter) and `expected`. Arguments and
answers are plain JSON. `NaN` and `Infinity` are rejected.

### Named checkers

| Checker | `expected` | Accepts |
| --- | --- | --- |
| `exact` | any JSON value | the same value (`true` is not `1`) |
| `any_order` | a list | the same items in any order, duplicates counted |
| `any_of` | a list of valid answers | any one listed answer |
| `indices_sum_to_target` | optional | any two distinct in-range indices into `args[0]` whose values sum to `args[1]` |

For predicate checkers such as `indices_sum_to_target`, `expected` is optional
and only shows one example answer in failure reports. The answer is judged from
the arguments, so any valid algorithm and order passes.

## Execution

1. The runner reads the solution bytes and hashes them.
2. A stub check reads the source (no execution). A top-level function whose body
   is only `pass`, `...`, a docstring, `raise NotImplementedError` or (when
   `allow_none` is false) `return None` is a stub. It is never run.
3. The solution runs in a child process: `sys.executable -I`, an empty temporary
   working directory, stdin closed. The worker imports the file, then calls the
   function once per case with arguments freshly decoded from JSON text. Expected
   answers are never sent to the child.
4. Results return on a private channel, so anything the solution prints cannot
   corrupt them. The tail of its stderr is kept for diagnostics.
5. One time limit covers the whole run (`--timeout`, default 10 seconds). On
   timeout the whole process tree is killed: `taskkill /F /T` on Windows (also
   ends the launcher process uv virtual environments use), a process group
   `SIGKILL` on POSIX. The POSIX path is written but only the Windows path has
   been exercised by the suite so far.

**This is not a security sandbox.** The child has the learner's own permissions
and can read files, use the network and spawn processes. The time limit only
limits runaway execution. Do not run untrusted code with it.

## Outcomes

Only `passed` is a pass. It requires a non-empty suite with every case passing.

| Status | Meaning |
| --- | --- |
| `passed` | every case in a non-empty suite passed |
| `failed` | wrong answer; the report names each case with actual and expected |
| `error` | import failure (including syntax errors), missing function, runtime exception, or the child died |
| `malformed` | an answer that is not JSON data, is `None` when forbidden, or has the wrong shape for the checker |
| `timeout` | the time limit was hit; finished cases keep their results |
| `stub` | the function is an unwritten placeholder; incomplete |
| `unsupported` | the contract names a language, adapter or checker the runner does not support |
| `no_suite` | `tests.json` is missing or has no cases |

When several kinds occur, the overall status is the first of: timeout, error,
malformed, failed. Case outcomes are `passed`, `failed`, `error`, `malformed`,
`timeout` or `not_run`.

## Evidence

The result (`RunResult`, printed with `--json`) holds:

- `code_sha256`: SHA-256 of the solution file bytes.
- `suite_sha256`: SHA-256 of the canonical JSON of the metadata plus the suite,
  so a change to the cases, expected answers or contract changes it. Formatting
  does not. `null` when there is no suite file.
- `suite_version`, `run_at` (UTC ISO 8601), `duration_seconds`,
  `timeout_seconds`, `platform`, `problem_id`.
- `cases`: per case `case_id`, `outcome`, `detail`, `expected`, `actual`.
- `notes`: on a timeout, a reminder that a timeout does not prove anything about
  asymptotic complexity.

Recording results to learner history is a separate ticket; `practice run` writes
no files.

## Command

```text
practice run PACKAGE_DIR SOLUTION_FILE [--timeout SECONDS] [--json]
```

| Exit code | Meaning |
| --- | --- |
| 0 | passed |
| 1 | ran but did not pass (any status other than `passed`) |
| 2 | usage error, including an unreadable solution file or a bad `--timeout` |
| 3 | invalid package or suite (reason on stderr) |

## Test fixture

`tests/fixtures/two_sum/` is a small Two Sum package used only by the runner
tests. The real Two Sum package lives in `problems/leetcode-1/`. Its solution
variants live in `tests/fixtures/two_sum_solutions/`: correct (hash map), an
alternate valid algorithm that answers in reverse order, wrong answer, two stubs,
runtime error, malformed output, import error, infinite loop and a noisy correct
solution.

## Starter file and attempt recording

A package may include an optional `starter.py`. `practice attempt start` copies it
byte for byte into the new attempt as `solution.py`; without it, a stub is
generated from the callable signature in `problem.json`. `practice attempt test`
runs the same runner and journals the outcome with `code_sha256` and
`suite_sha256`. See [learner history](learner-history.md).
