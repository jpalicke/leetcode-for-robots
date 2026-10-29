# Published DSA references: source research and proposed policy

Prepared for Joe P. Checked 2026-10-28. Research and planning only.
Four files have been imported as a demonstration of the intake path
([source intake](source-intake.md)): the NeetCode Python Two Sum, Contains
Duplicate, Valid Anagram and Valid Parentheses solutions. No
upstream suite was executed, and no candidate implementation has been
independently verified as accepted on LeetCode.
Joe P approved the six-source initial pool in section 4. Detailed verification and import procedures remain under discussion.

## Confirmed requirement

Store reference code locally with citations to published sources. Include general
DSA teaching material as well as problem-specific solutions. Settle the source
policy before implementation resumes.

Published implementations are preferred rather than mandatory. A clearly labeled
agent-written reference may fill a gap after the same independent validation.
Publication status, local test evidence, and platform acceptance remain separate;
do not invent a citation or acceptance record for generated material.

Joe P approved preserving published reference implementations and notices
unchanged, with local test/execution adapters kept separately. Identify adapted
implementations separately and record their relationship to the original source.

Joe P confirmed that the project is intended for noncommercial use. Sources
with noncommercial terms remain eligible candidates; they are not excluded
for lacking commercial-use permission. Preserve each selected source's actual
terms and notices. This settles intended use, not the entire source-selection policy.

The findings below distinguish published license declarations from our engineering
assessment of usefulness. Approval applies to selected files and versions, not
indiscriminately to everything hosted by a project. Source links generally point
to moving branches; approved imports need exact revision pins.

## 1. Strong candidates for a reusable core

| Source | Published terms and evidence | Teaching/reference role | Qualification |
| --- | --- | --- | --- |
| [OpenDSA](https://github.com/OpenDSA/OpenDSA) | [MIT project license](https://raw.githubusercontent.com/OpenDSA/OpenDSA/master/MIT-license.txt); sampled teaching modules also carry MIT headers | Explanations, prerequisite maps, algorithm analysis, exercises, and traces; Python/C++/Java and other source directories | Strong tutor knowledge candidate. Check chosen modules and dependencies. Text extraction alone loses interactive visualization behavior. Language directories do not imply equal coverage. |
| [Open Data Structures](https://opendatastructures.org/) | Site declares book/source reusable with attribution; [COPYING](https://raw.githubusercontent.com/patmorin/ods/master/COPYING) links [CC BY 2.5 Canada](https://creativecommons.org/licenses/by/2.5/ca/) | Rigorous implementation and analysis of lists, queues, hashing, trees, heaps, and graphs; Python/pseudocode, Java, C++ | Strong data-structure foundation. COPYING names specific directories and separately identifies third-party Java test code; check exact selected paths. Some code/style is older and needs compatibility validation. |
| [Algorithms, Jeff Erickson](https://jeffe.cs.illinois.edu/teaching/algorithms/) | Author identifies the 2019 textbook as CC BY 4.0; other lecture notes are CC BY-NC-SA 4.0 | Correctness reasoning, recursion, recurrences, DP, greedy methods, graphs; language-neutral pseudocode | Strong deeper reasoning companion. Not a first DSA introduction or runnable solution collection. Treat the book, other notes, and credited artwork separately. [Source repository](https://github.com/jeffgerickson/algorithms). |
| [TheAlgorithms/Python](https://github.com/TheAlgorithms/Python) | [MIT](https://raw.githubusercontent.com/TheAlgorithms/Python/master/LICENSE.md) | Broad educational implementation examples; selected doctests and pytest-based CI | Good Python code companion. Explanatory depth varies; upstream explicitly says educational implementations may be less efficient than standard-library versions. Inspect each contract and test selected files locally. |
| TheAlgorithms [C++](https://github.com/TheAlgorithms/C-Plus-Plus), [Rust](https://github.com/TheAlgorithms/Rust), and [Go](https://github.com/TheAlgorithms/Go) | MIT: [C++](https://raw.githubusercontent.com/TheAlgorithms/C-Plus-Plus/master/LICENSE), [Rust](https://raw.githubusercontent.com/TheAlgorithms/Rust/master/LICENSE), [Go](https://raw.githubusercontent.com/TheAlgorithms/Go/master/LICENSE) | Future language companions with independent implementations | Rust has cargo-test/clippy configuration; Go configures go test; C++ commonly embeds self-tests in programs. Interfaces and coverage differ across repositories. |
| [Python documentation](https://docs.python.org/3/library/collections.html) | [License page](https://docs.python.org/3/license.html): PSF v2 for documentation; code examples also dual-licensed under 0BSD starting with Python 3.8.6 | Authoritative semantics and examples for Python containers and library operations | Useful for syntax, built-ins, and language-specific explanations. Pin documentation to the supported Python version. It is not a full DSA curriculum. |
| [PyRival](https://github.com/cheran-senthil/PyRival) | [Apache-2.0](https://raw.githubusercontent.com/cheran-senthil/PyRival/master/LICENSE) | Advanced Python graph, string, number-theory, and range-query algorithms | Good later supplement and candidate independent comparison implementation. Contest-oriented code can be terse. [Judge-verification workflow](https://github.com/cheran-senthil/PyRival/blob/master/.github/workflows/verify.yml) is evidence of configured checks, not our own validation. |
| [Learning Rust With Entirely Too Many Linked Lists](https://rust-unofficial.github.io/too-many-lists/) | [MIT](https://raw.githubusercontent.com/rust-unofficial/too-many-lists/master/license-MIT) | Rust ownership, borrowing, iterators, pointer types, and implementation tradeoffs | Future language-specific supplement. Deliberately flawed intermediate examples are teaching stages, not ready reference answers. Narrow topic coverage. |

## 2. Problem-specific published solution candidates

| Source | Published terms | Value | Verification limit |
| --- | --- | --- | --- |
| [NeetCode solution repository](https://github.com/neetcode-gh/leetcode) | [MIT](https://raw.githubusercontent.com/neetcode-gh/leetcode/main/LICENSE) | Python plus C++, Rust, Go and others; recognizable interview-practice selection; supports multiple approaches | [Contribution rules](https://raw.githubusercontent.com/neetcode-gh/leetcode/main/CONTRIBUTING.md) require successful LeetCode submission. This is an author/contributor requirement, not independently checked acceptance evidence for every file. Repository scope does not establish rights to all related videos or website material. |
| [walkccc/LeetCode](https://github.com/walkccc/LeetCode) | [MIT](https://raw.githubusercontent.com/walkccc/LeetCode/main/LICENSE) | Readable Python/C++ implementations and complexity annotations; broad problem coverage | Coverage is incomplete and differs by language. A solution being published here does not give us an inspected platform submission record. [Sample page](https://walkccc.me/LeetCode/problems/1/). |
| [Doocs LeetCode](https://github.com/doocs/leetcode) | [CC BY-SA 4.0](https://raw.githubusercontent.com/doocs/leetcode/main/LICENSE) | Broad multilingual solutions and written explanations, including Python/C++/Rust/Go | Strong supplementary candidate if share-alike material is included under an explicit policy. Distinguish project-authored explanations/code from reproduced problem statements and other third-party content. |
| [LeetCode editorials and community solutions](https://leetcode.com/problems/two-sum/editorial/) | No general open-source copying permission established in this research; [published terms](https://leetcode.com/terms/) apply | Official explanations and external citations; specific accepted submissions can provide execution evidence | Ordinary page access does not establish redistribution rights. The pages fetched here exposed navigation rather than editorial contents. Prefer clearly licensed publisher repositories for local code imports. Do not treat every community post as a verified accepted solution. |

Sampled judge-oriented code can omit imports or depend on supplied types. A local
execution adapter must account for that without silently changing the reference
or claiming that an adapted version inherits the original acceptance evidence.

## 3. Useful sources requiring a deliberate additional policy

These sources remain in the candidate inventory. Different terms or narrower fit
are reasons to discuss their role, not a claim that they have no value.

| Source | Published terms and evidence | Useful role | Decision needed |
| --- | --- | --- | --- |
| [cp-algorithms](https://cp-algorithms.com/) | [CC BY-SA 4.0](https://raw.githubusercontent.com/cp-algorithms/cp-algorithms/main/LICENSE); [auxiliary C++ library](https://github.com/cp-algorithms/cp-algorithms-aux) also declares CC BY-SA | Deep explanations, complexity, proofs, and mostly C++ examples for medium/hard material | Decide how to preserve share-alike content and adaptations. Do not label its snippets or auxiliary library MIT. |
| [Hello Algo](https://www.hello-algo.com/en/) | [README declaration](https://github.com/krahets/hello-algo#license) and [license](https://raw.githubusercontent.com/krahets/hello-algo/main/LICENSE): CC BY-NC-SA 4.0 covers text, code, images, photos, and videos | Excellent visual beginner material, with Python/C++/Rust/Go support | Its inspected current policy does not provide an MIT-code exception. Eligible for the intended noncommercial scope; source selection and attribution/share-alike treatment remain to be specified. |
| [Runestone: Problem Solving with Algorithms and Data Structures using Python](https://runestone.academy/ns/books/published/pythonds3/index.html) | [Book repository license](https://raw.githubusercontent.com/RunestoneInteractive/pythonds/master/LICENSE.txt): CC BY-NC-SA 4.0 | Particularly strong Python-first teaching, alternative approaches, self-checks, and complexity comparisons | Book rights differ from the hosting platform's software license. No permissive code-snippet exception was established. Eligible for the intended noncommercial scope; preserve the book-specific terms. |
| [AtCoder Library](https://github.com/atcoder/ac-library) | [CC0-1.0](https://raw.githubusercontent.com/atcoder/ac-library/master/LICENSE); documentation frontend dependencies have separate terms | Focused C++ algorithms with precise contracts and tests; useful future independent checks | Strong code candidate, but narrower and more advanced than our first six exercises. Observe algorithm preconditions and exclude unrelated documentation assets. |
| [KACTL](https://github.com/kth-competitive-programming/kactl) | [File-specific licensing policy](https://github.com/kth-competitive-programming/kactl#license) explicitly reports mixed/unclear coverage | Compact C++ algorithms and stress-test examples | Select individually licensed files only; no blanket CC0 assumption. Terse templates are less suitable for first explanations. |
| [OI Wiki](https://github.com/OI-wiki/OI-wiki) | [Rights declaration](https://github.com/OI-wiki/OI-wiki#版权声明) distinguishes non-code content and adds SATA terms | Broad mostly Chinese DSA/competitive-programming explanations, often C++ | Exact code-snippet terms remain unresolved. Do not infer snippet licensing from frontend software licenses. Keep as a citation candidate until selected material is clarified. |
| [Princeton algs4](https://github.com/kevin-wayne/algs4) | [GPLv3 code license](https://raw.githubusercontent.com/kevin-wayne/algs4/master/LICENSE); sampled source headers say version 3 or later | Strong textbook-oriented Java algorithms and documented contracts | Java is outside the requested language roadmap. Keep source-code licensing distinct from the commercial textbook and website prose. |

## 4. Approved initial source pool

Joe P approved selected material from these six sources:

| Role | Sources |
| --- | --- |
| Teaching | Runestone and Hello Algo |
| General DSA references | OpenDSA and TheAlgorithms |
| LeetCode-specific implementations | NeetCode and walkccc |

Individual files will be checked and validated as each problem is prepared, with
original code/notices preserved and local adapters separate. The other researched
sources remain in the inventory for possible later supplementation; they are not
part of this approved initial pool. Only the single NeetCode demonstration file
has been imported, preserved unchanged under `references/` with its notice and a
provenance manifest. It has no local validation and no recorded platform
acceptance. No other code has been imported.

A perfectionist would require independently inspected platform acceptance for
every applicable solution before admitting it. A pragmatist would accept strong
local validation with explicit provenance, recording platform acceptance when
available. Joe P selected the latter threshold: local tests and independent
correctness checks are required; verified LeetCode acceptance is additional
evidence when available and is not a prerequisite. This rule applies equally to
published, adapted, and agent-written reference implementations.

## 5. Proposed per-reference admission record

Keep these independent facts rather than collapsing them into one trust label:

1. Identity: platform/problem or general DSA concept, language, and approach.
2. Provenance: publisher/author, exact repository commit and file path, source URL,
   acquisition date, original hash, and local hash.
3. Reuse evidence: exact published license, required notices, and any file-level
   exceptions or dependencies. Preserve the applicable source/license material.
4. Transformation: unchanged, adapted, translated, or agent-authored supplement,
   with the actual changes recorded.
5. Execution contract: runtime, imports, supplied node types, preconditions,
   mutation/output semantics, and adapter version.
6. Correctness evidence: reasoning reviewed, upstream tests available, independent
   local checks run, test suite version, result, and date.
7. Platform evidence: unknown, author-reported accepted, or independently inspected
   accepted submission. Include submission/date/code-version evidence when available.
8. Teaching classification: complete solution, implementation example, concept
   explanation, worked example, exercise question, exercise answer, or known-broken
   teaching stage; attach spoiler level and prerequisites.

Tests should validate the actual runnable local version. A translation or changed
implementation does not automatically inherit acceptance from the source. A
published reference is evidence to evaluate, not a rule that every learner must
match its code or complexity.

## 6. Tutor and RAG implications

A general DSA chapter can reveal a problem's intended technique just as clearly
as solution code. Split concept text, worked examples, complete implementations,
exercise questions, and answers into separately classified units. Apply mode and
reveal rules before selecting context. Keep citations and license provenance with
each unit and preserve them in exports.

Maintaining a local reference collection is distinct from displaying its contents.
Practice mode withholds solution-bearing material until the agreed assistance
level permits it. Repository instructions guide behavior and are not a guarantee
that an unrestricted agent cannot read a file.

## 7. Remaining implementation details

The initial pool, noncommercial intent, preference for published implementations,
source preservation approach, and reference-validation threshold are agreed.
The implementation plan will define exact revision pins, per-file notices,
source-specific attribution/share-alike handling, adapters, and validation commands.

Catalog metadata comes from `https://leetcode.com/api/problems/all/`, an unofficial
endpoint. Problem statements are stored as a link to LeetCode plus our own short
summary, never copied text. Before mixing share-alike or noncommercial sources, a
stated policy must say how each unit records its terms (required before #6).
No reference import or implementation has begun.
This research is a source-selection aid. It does not claim a full audit of every
candidate file, successful execution of any upstream test suite, complete catalog
coverage by a source, or a resolved license policy for the combined repository.
