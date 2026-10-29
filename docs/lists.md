# Curated problem lists

A list is an ordered, grouped set of catalog problems published by someone else:
LeetCode Top Interview 150, Blind 75 and so on. Lists are an overlay on the catalog.
Each catalog problem still belongs to exactly one preparation ticket (see #15); a
problem in several lists is counted once for coverage and shown in each list.

## Reading them

```text
uv run --locked practice lists
uv run --locked practice lists show blind-75
uv run --locked practice lists show blind-75 --json
uv run --locked practice lists check
```

`practice lists` shows each list with its size and how many problems are ready,
blocked and pending. `show` prints the problems in list order under the list's own
group headings, with one status each:

| Status | Meaning |
| --- | --- |
| `[ready]` | the exercise package passes `practice readiness` |
| `[blocked]` | a premium problem with no package |
| `[pending]` | everything else; never shown as runnable |

`--json` prints the same facts, with a `reason` on every problem that is not ready.
`check` validates every file. A bad file refuses every `lists` command (exit 3) and
nothing else is printed. An unknown list id exits 1 and names the known lists.
`--lists-dir` points the commands at another folder.

## The lists

| Id | Name | Problems | Source |
| --- | --- | --- | --- |
| `top-interview-150` | LeetCode Top Interview 150 | 150 | LeetCode study plan |
| `leetcode-75` | LeetCode 75 | 75 | LeetCode study plan |
| `top-100-liked` | LeetCode Top 100 Liked | 100 | LeetCode study plan |
| `programming-skills` | LeetCode Programming Skills | 33 | LeetCode study plan |
| `binary-search` | LeetCode Binary Search | 32 | LeetCode study plan |
| `dynamic-programming` | LeetCode Dynamic Programming | 46 | LeetCode study plan |
| `graph-theory` | LeetCode Graph Theory | 36 | LeetCode study plan |
| `blind-75` | Blind 75 | 75 | NeetCode site data |
| `neetcode-150` | NeetCode 150 | 150 | NeetCode site data |
| `neetcode-all` | NeetCode All | 450 | NeetCode site data |

These are the lists that were confirmed to exist and to match the catalog. They are
not every list on the internet, and the project does not claim to know them all:
LeetCode offers no index of its study plans that a tool can read, so each list is
named on purpose. Left out of the first set because every problem in them is
specialized and blocked for the current runner: SQL 50, 30 Days of JavaScript, 30 Days
of Pandas, Introduction to Pandas and the company high-frequency plans.

## What a list file holds

One file per list in `catalog/lists/`, named for its id: `schema_version`, `id`,
`name`, `platform`, `size`, a `source` and ordered `groups` of `{id, slug}`. Only
problem numbers and slugs are stored, never problem text. Validation against the
catalog checks that every problem exists with the same number and slug, that none
repeats inside a list, that the group sizes add up to `size`, and that `source` has a
kind, an https address, a retrieval date and (for NeetCode) the pinned revision and
license. Unknown keys are rejected. Premium problems stay in the list.

## Adding or refreshing a list

`catalog/list-sources.json` names every list and where it comes from. The tool reads
it:

```text
uv run --locked python tools/fetch_lists.py fetch
uv run --locked python tools/fetch_lists.py fetch --only blind-75
uv run --locked python tools/fetch_lists.py fetch --check
uv run --locked python tools/fetch_lists.py add --leetcode-plan https://leetcode.com/studyplan/top-interview-150/ --id my-list --name "My list"
uv run --locked python tools/fetch_lists.py add --neetcode-flag blind75 --id my-blind --name "My Blind 75"
```

- `fetch` rebuilds the files. It fetches and validates every requested list first and
  writes only if all of them are good, so a failure leaves the committed files alone.
- `fetch --check` compares the committed files with the sources (ignoring the
  retrieval date) and exits 1 on any difference. It needs the network.
- `add` takes a study plan slug or address, or a NeetCode data flag (`*` for every
  row), registers it and fetches it. A plan that does not exist changes nothing.
- Requests to LeetCode are spaced by `--delay` seconds (default 1.5). Only https is
  allowed, or http on a loopback address for tests. Redirects are not followed and a
  response over 8 MiB is refused.
- NeetCode's file numbers are not always LeetCode's: one row (maximum alternating
  subsequence sum) carries 5782 where LeetCode's number is 1911. The tool takes the
  number from the catalog by slug and prints a warning for every disagreement.

## Sources and terms

- LeetCode study plans are read from LeetCode's GraphQL endpoint, which is unofficial
  and not a supported contract. Only problem numbers, slugs and the plan's group names
  are kept. Check LeetCode's terms of use before refreshing in bulk.
- NeetCode lists come from `.problemSiteData.json` in `neetcode-gh/leetcode` at the
  pinned revision recorded in the registry, an MIT-licensed repository that the
  reference sources already use. Blind 75 is NeetCode's flag for that popular list;
  the original list is not a source here.
- The list selections belong to their publishers. This project records which
  problems they name, as a pointer, and does not copy their explanations.

## Verified against the sources

On 2026-10-29 all ten lists were fetched from the live sources and written, and
`tools/fetch_lists.py fetch --check` then reported that all ten match. The tool's
tests run it against a real local HTTP server, with no network and no mocking.
