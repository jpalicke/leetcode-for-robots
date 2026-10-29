# Study mode

Study mode is the one place the tutor may teach a concept openly before you try the
exercise. It is your explicit choice. Practice mode, untimed, is always the default,
and nothing in the menus or the tutor switches to study mode for you.

## What it is

- You pick the Study item in `practice menu` or `practice tui` (item 6 on the main
  menu), then pick a problem. That starts an attempt with mode `study`, recorded in
  your private journal like any other attempt.
- The menu prints the exact `practice knowledge export` command for each study unit
  of that problem, a paste-ready request to give the tutor, and a citation and
  license line for every unit. The menu never sends anything and never records help
  as given.
- Study mode explains concepts. It does not authorize the full solution (TUTOR-002).
  The answer for your exercise is still yours to write.

## How units are stored and cited

A study unit is one real upstream file, fetched with `practice sources add`, pinned
to a commit SHA, and preserved byte for byte with the upstream license notice under
`references/upstream/<id>/`. Its manifest is `references/manifests/<id>.json`. Nothing
under `references/upstream/` is ever edited.

Concept prose is classified `teaching_explanation`. A file that carries solution code
or a worked example gets a spoiler class instead (`algorithm_implementation` or
`reference_solution`), and the export refuses it unless you also ask for a full
solution reveal. The class list lives in `src/practice/classification.py`.

A problem lists its units in `readiness.json`:

```json
"knowledge_sources": ["hello-algo-hash-table-concept"]
```

This is a plain association list. `practice readiness` and `practice sources verify`
check it, and `practice knowledge export ... --mode study --source ID` honors it.

## The units today

| Unit ID | Concept | Source (pinned) | Class | License |
| --- | --- | --- | --- | --- |
| `hello-algo-hash-table-concept` | Hash table, set, map | Hello Algo `hash_map.md` @ `2f561d3d51878063a02667ab7903962f009925f4` | `teaching_explanation` | CC-BY-NC-SA-4.0 |
| `hello-algo-array-concept` | Array traversal | Hello Algo `array.md` @ `2f561d3d51878063a02667ab7903962f009925f4` | `teaching_explanation` | CC-BY-NC-SA-4.0 |
| `hello-algo-binary-search-concept` | Binary search | Hello Algo `binary_search.md` @ `2f561d3d51878063a02667ab7903962f009925f4` | `teaching_explanation` | CC-BY-NC-SA-4.0 |
| `runestone-pythonds-stack-concept` | Stack | Runestone `WhatisaStack.rst` @ `946c02ed651768bc99ea9751961fabd20bb8194d` | `teaching_explanation` | CC-BY-NC-SA-4.0 |
| `opendsa-hashing-introduction-concept` | Hashing introduction | OpenDSA `HashIntro.rst` @ `f900a7aa3d7fd4289b82a767e4958974eb3e9d17` | `teaching_explanation` | MIT |

Problems 1, 20, 121, 217, 242 and 704 each list the units for their concepts.

## Terms

Hello Algo and Runestone are CC BY-NC-SA 4.0: give credit, link the license and
indicate changes; noncommercial use only; share adaptations under the same license.
This project is noncommercial (approved by Joe P in
[reference sources](reference-sources.md)). The share-alike and noncommercial terms
stay with each unit: the file is unchanged, cited with its license, and any
adaptation must keep the same license. OpenDSA is MIT. Each manifest records the
terms read from the fetched notice, and the handoff prints them with the citation.

## How practice mode stays closed

Practice mode keeps study units out in three ways.

1. `practice knowledge export` admits `teaching_explanation` prose only with
   `--mode study` and an explicit `--source`. In practice mode it exits 3 with
   "excluded by the selected reveal scope".
2. A practice-mode concept refresher request tells the tutor to ask you first and
   treat your answer as a hint request. It carries no study unit.
3. Only the Study menu item starts a study-mode attempt, and the choice covers that
   attempt only.

Tests cover each of these against the real units.

## Adding a unit

1. Pick a file from an approved source (Runestone, Hello Algo or OpenDSA) at a commit
   you can pin. Prefer concept prose. Read the file: solution code or a worked example
   means a spoiler class.
2. Run `practice sources add` with the raw URL at the pinned SHA, the notice URL, and
   the class. Read the fetched notice and record its terms. A non-permissive license
   needs a `policy_note`.
3. Add the new ID to `knowledge_sources` in each relevant `readiness.json`.
4. Run `practice sources verify`, `practice readiness PLATFORM ID`, and the test suite.
5. Search the docs for the old wording of any rule you changed.
