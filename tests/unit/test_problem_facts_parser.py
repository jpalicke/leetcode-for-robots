# ABOUTME: Checks extraction of invented problem facts without executing snippets.
# ABOUTME: Rejects incomplete or ambiguous source material instead of guessing facts.

import json

import pytest

from tools.fetch_problem_facts import ToolError, parse_facts

HTML = """<p>Invented widget task.</p><p><strong>Example 1:</strong></p>
<pre><strong>Input:</strong> widgets = [7,8]
<strong>Output:</strong> 15
<strong>Explanation:</strong> Add &lt;two&gt; widgets.</pre>
<p><strong>Example 2:</strong></p><pre>Input: widgets = [0]
Output: 0</pre><p><strong>Constraints:</strong></p>
<ul><li><code>1 &lt;= widgets.length &lt;= 10<sup>5</sup></code></li>
<li>Each w<sub>i</sub> is &gt;= 0.</li></ul>
<p>Follow-up:</p><ul><li>Do not collect this.</li></ul>"""
CODE = (
    "class Solution:\n    def widgetSum(self, widgets: List[int]) -> int:\n"
    "        pass\n"
)


def response(html: str = HTML, code: str = CODE) -> bytes:
    return json.dumps(
        {
            "data": {
                "question": {
                    "questionId": "999",
                    "questionFrontendId": "LCR 999",
                    "titleSlug": "widget-sum",
                    "title": "Widget Sum",
                    "isPaidOnly": False,
                    "content": html,
                    "codeSnippets": [{"langSlug": "python3", "code": code}],
                }
            }
        }
    ).encode()


def test_extracts_all_examples_math_and_distinct_ids() -> None:
    facts = parse_facts(response(), "widget-sum", "https://example.org/graphql")
    assert (
        facts["python3_signature"] == "def widgetSum(self, widgets: List[int]) -> int:"
    )
    assert facts["constraints"] == [
        "1 <= widgets.length <= 10^5",
        "Each w_i is >= 0.",
    ]
    assert facts["examples"] == [
        {
            "number": 1,
            "input": "widgets = [7,8]",
            "output": "15",
            "explanation": "Add <two> widgets.",
        },
        {"number": 2, "input": "widgets = [0]", "output": "0"},
    ]
    assert facts["question_id"] == "999"
    assert facts["frontend_question_id"] == "LCR 999"
    assert "content" not in facts


def test_paragraph_example_layout() -> None:
    html = """<p><b>Example 1:</b></p><div class="example-block">
<p><b>Input:</b> x = &quot;ab&quot;</p><p><b>Output:</b> &quot;a&quot;</p>
<p><b>Explanation:</b> First<br>letter.</p></div>
<p>Constraints:</p><ul><li>x has two letters.</li></ul>"""
    facts = parse_facts(response(html), "widget-sum", "https://example.org/graphql")
    assert facts["examples"][0]["explanation"] == "First\nletter."


def test_empty_final_method_suite_is_a_platform_stub() -> None:
    code = (
        "class Solution:\n    def widgetSum(self, widgets: list[int]) -> int:\n        "
    )
    facts = parse_facts(
        response(code=code), "widget-sum", "https://example.org/graphql"
    )
    assert (
        facts["python3_signature"] == "def widgetSum(self, widgets: list[int]) -> int:"
    )


def test_complex_math_and_self_closing_breaks_preserve_meaning() -> None:
    html = HTML.replace("10<sup>5</sup>", "2<sup>n+1</sup>")
    html = html.replace("Add &lt;two&gt; widgets.", "First<br />second.")
    facts = parse_facts(response(html), "widget-sum", "https://example.org/graphql")
    assert facts["constraints"][0] == "1 <= widgets.length <= 2^(n+1)"
    assert facts["examples"][0]["explanation"] == "First\nsecond."


def test_example_string_spaces_are_not_collapsed() -> None:
    html = HTML.replace("widgets = [7,8]", 's = "a  b"')
    facts = parse_facts(response(html), "widget-sum", "https://example.org/graphql")
    assert facts["examples"][0]["input"] == 's = "a  b"'


def test_prose_outside_example_container_is_not_silently_saved() -> None:
    html = HTML.replace("Output: 0</pre>", "Output: 0</pre><p>Unrelated prose.</p>")
    with pytest.raises(ToolError, match="outside example"):
        parse_facts(response(html), "widget-sum", "https://example.org/graphql")


@pytest.mark.parametrize(
    "code",
    [
        "class Solution: broken syntax!",
        "class Solution:\n    def a(self): pass\n    def b(self): pass",
        "class Other:\n    def a(self): pass",
        "class Solution:\n    @staticmethod\n    def a(): pass",
    ],
)
def test_rejects_unsupported_signature(code: str) -> None:
    with pytest.raises(ToolError, match="Python3"):
        parse_facts(response(code=code), "widget-sum", "https://example.org/graphql")


@pytest.mark.parametrize(
    "html",
    [
        HTML.replace("Output: 0", "Answer: 0"),
        HTML.replace("Example 2:", "Example 3:"),
        HTML.replace("Constraints:", "Bounds:"),
        HTML.replace("<sup>5</sup>", '<img src="formula">'),
    ],
)
def test_rejects_missing_or_unsupported_content(html: str) -> None:
    with pytest.raises(ToolError):
        parse_facts(response(html), "widget-sum", "https://example.org/graphql")


@pytest.mark.parametrize(
    "mutation", ["paid", "flag", "slug", "null", "errors", "duplicate"]
)
def test_rejects_platform_schema_failures(mutation: str) -> None:
    payload = json.loads(response())
    q = payload["data"]["question"]
    if mutation == "paid":
        q["isPaidOnly"] = True
    elif mutation == "flag":
        q["isPaidOnly"] = "false"
    elif mutation == "slug":
        q["titleSlug"] = "other"
    elif mutation == "null":
        payload["data"]["question"] = None
    elif mutation == "errors":
        payload["errors"] = [{"message": "rejected"}]
    else:
        q["codeSnippets"] *= 2
    with pytest.raises(ToolError):
        parse_facts(
            json.dumps(payload).encode(), "widget-sum", "https://example.org/graphql"
        )
