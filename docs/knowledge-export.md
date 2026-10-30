# Source-aware knowledge export

`uv run --locked practice knowledge export PLATFORM ID` emits deterministic JSON
on stdout. Global `--problems-dir`, `--references` and `--practice-dir` flags go
before `knowledge`. It reads metadata only from the selected
`problems/<platform>-<id>/problem.json` and `readiness.json`, verifies their identity
and language, and selects public content before assembling bodies. It never reads
tests, learner journals, attempts or assistance records and creates no learner state.
No model, network, embedding service or vector database is involved.

```text
uv run --locked practice knowledge export leetcode 1 --language python
uv run --locked practice knowledge export leetcode 1 --hint-level 2
uv run --locked practice knowledge export leetcode 1 --reveal-solution
uv run --locked practice knowledge export leetcode 1 --reveal-solution --source neetcode-leetcode-0001-two-sum-python --output knowledge.json
```

`--mode practice` is the default. Only the classified `statement_summary` is
selected automatically. `--hint-level N` selects exactly that level, not earlier
levels. Hint filenames are relative to the directory containing the metadata-named
hint index. `--reveal-solution` selects classified problem notes and may admit
explicitly selected reference solutions or algorithm implementations. These two
reveal options are mutually exclusive. No reference is selected automatically.

Repeat `--source ID` to select registered sources associated with this problem in
`readiness.references.upstream`, `.adaptations`, or `.originals`. A readiness record
may also carry `"knowledge_sources": ["source-id"]` for cited teaching units. This
is an association list using the existing source manifests, not another global
index. Wrong-language, unrelated and unknown sources fail clearly.

`--mode study --source ID` can admit selected `teaching_explanation` prose (Markdown,
plain text or reStructuredText). General DSA prose can reveal the current problem's
strategy, so practice mode excludes it even though the shared vocabulary does not
mark it as a spoiler. Study mode (see [study mode](study-mode.md)) does not authorize complete solutions or source
code. Code needs explicit `--source` plus `--reveal-solution`; test data and every
learner content class stay excluded in every mode. Registered hint sources are
excluded: select a numbered problem hint instead.

Export enforces declared classifications, not semantic spoiler detection.
Reviewers must keep statement summaries neutral and classify DSA explanations
honestly because apparently general explanations can reveal the intended strategy.

Selection never checks excluded solution, reference or hint bodies. Missing or
unreadable excluded files therefore do not break a default export. Selected paths
reject traversal, absolute paths, escaping symlinks, `.practice` and learner-class
directories, and the resolved custom practice directory. Selected references use
the existing manifest schema and citation verification for hashes, lineage and
notice integrity. Preserved upstream files and notices are never rewritten.

Schema version 1 contains `documents`, each with logical problem/language/role,
content kind, reveal scope, source ID, revision, source/content SHA-256 and chunks.
Document IDs hash the logical problem, language, role and source identity; chunk
IDs add a zero-based ordinal. IDs do not change merely because text changes;
content hashes do. Chunks are at most 2,000 Unicode characters, preferring a line
boundary, and concatenate to the exact decoded UTF-8 bytes including line endings.
The document hash covers original UTF-8 bytes. Source citations retain origin URL,
revision, file and notice hashes, terms and license identifier. Notice text is
included unchanged. Project-authored summaries and notes identify their provenance
as project-authored, with no invented upstream license or revision.

Sorted JSON keys, stable document ordering and logical IDs make repeated exports
and exports from copied identical inputs byte-identical. No machine-specific
absolute paths or generated timestamps are added; recorded source acquisition
metadata is retained. `--output PATH` exclusively creates a UTF-8/LF file and
refuses existing files, protected input directories and private paths. Exit 0 means
exported, 2 means CLI usage error, and 3 means invalid selected input or output.

Verification scenarios use real files and processes: default export with deleted
excluded bodies and corrupt test data; exact-level hints; explicit solutions;
registered references with notices and tampered hashes; teaching versus solution
scope; identity/class/path failures; stable IDs across content changes and copied
roots; and exclusive output creation. The clean-checkout scenario also exports
LeetCode 1 and asserts no `.practice` directory appears.

The [RAG comparison design](rag-experiment.md) uses these exports as the shared
permission boundary for direct context and retrieval. Its versioned pilot fixtures
are evaluation inputs, not a retrieval backend or measured model results.
