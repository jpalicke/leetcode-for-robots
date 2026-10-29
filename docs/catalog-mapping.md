# Catalog mapping

Every one of the 4096 problems in `catalog/problems.json` belongs to exactly one
preparation ticket. The mapping is a committed plan, not a set of hand-made issues.
This page covers how the plan is built, how to read it and how to change it.

Status: the plan exists and is checked. Creating the GitHub tickets is a separate,
deliberate step that a person runs after reading the plan (see the last section).

## Files

| File | What it is |
| --- | --- |
| `catalog/leetcode-topics.json` | Category and topic tags for every catalog problem, fetched from LeetCode. |
| `catalog/class-rules.json` | The rules that turn facts into classes: ticket size, specialized groups, concept priority. |
| `catalog/ticket-plan.json` | The generated plan: every ticket and the problems in it. |

## How a problem gets its ticket

The first rule that matches wins.

1. **Individual ticket.** The six starter problems keep their existing issues
   (#20 to #25).
2. **Specialized group.** Premium, SQL, pandas, shell, concurrency, JavaScript,
   interactive and design problems cannot go through the Python exercise flow, so
   they are grouped by reason and stay blocked.
3. **Concept class.** The remaining algorithm problems go to the highest-priority
   concept among their topic tags (dp, graphs, trees, linked, lookup, strings,
   sequences, arrays), then by difficulty.
4. **Fallback.** Problems with no usable tag go to `uncategorised`.

A class larger than 100 problems is split into balanced tickets. Titles read like
`Prepare dynamic programming problems, medium (2 of 3)`.

## Commands

```text
uv run --locked python tools/fetch_catalog_topics.py          # refresh topic facts
uv run --locked python tools/plan_catalog.py plan             # write or update the plan
uv run --locked python tools/plan_catalog.py check            # fail if the plan is incomplete or stale
uv run --locked python tools/plan_catalog.py report           # coverage by status, ticket and list
uv run --locked python tools/plan_catalog.py render dp-easy-01  # the body a ticket would get
```

`plan` reconciles with the existing plan instead of redoing it. A problem keeps its
ticket when the catalog changes, new problems fill the smallest open ticket of their
class, and a problem that leaves the catalog is flagged, not dropped. Issue numbers
and `in_progress` states are preserved. `plan --rebuild` regroups from scratch.

A ticket's status follows its problems: it is `ready` only when every problem passes
`practice readiness`, `blocked` for the specialized groups, and `pending` otherwise.

## Lists

Curated lists (Top Interview 150, Blind 75 and the rest) are an overlay. They add no
tickets. `plan_catalog.py report` shows, for each list, how many of its problems are
ready, blocked or pending.

## Changing the rules

Edit `catalog/class-rules.json`, run `plan`, read the diff of `ticket-plan.json`, and
commit both. A topic tag with no concept mapping stops the tool and names the tag, so
a new LeetCode topic cannot silently change a class.

## Creating the GitHub tickets

`tools/create_catalog_tickets.py` turns the plan into GitHub issues. It is a dry run
unless you pass `--apply`, so nothing is written by accident.

```text
uv run --locked python tools/create_catalog_tickets.py            # dry run, read-only
uv run --locked python tools/create_catalog_tickets.py --apply    # create and link
```

It needs a GitHub token in `GITHUB_TOKEN` for `--apply`. The dry run reads with the
token when there is one.

- **Which tickets:** every planned class ticket whose `issue` is `null`. The six
  starters keep their own issues and are never touched.
- **Duplicate-safe:** before creating, it searches the repository for an issue with
  exactly the planned title and adopts it. Two matches stop the run.
- **Resumable:** the new issue number is written into `ticket-plan.json` after each
  ticket. A crash leaves what was done, and a rerun finishes the rest. A ticket that
  has an issue but is not yet under the parent is linked on the next run.
- **Linked:** each class ticket is added as a sub-issue of #1 (`--parent` changes it).
- **Rate-limited:** one request at a time, `--delay` seconds apart (default 2).
- **Body:** the text of `plan_catalog.py render <ticket>`, minus its title line.

After an `--apply`, commit the updated `catalog/ticket-plan.json` so the issue
numbers are recorded, and run `plan_catalog.py check`.
