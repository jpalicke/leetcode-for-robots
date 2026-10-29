# 20. Valid Parentheses (Easy)

Original problem: <https://leetcode.com/problems/valid-parentheses/>. This page is
our own short summary, not the platform's text. Read the original for its exact
wording.

## Task

You get a string `s` made only of the six characters `(`, `)`, `[`, `]`, `{` and `}`.
Say whether the brackets are properly matched. Every opening bracket has to be closed
by a bracket of the same kind, and brackets have to close in the right order: the
most recently opened one that is still open must be the next one to close.

## What you write

LeetCode asks for a method on a class:

```python
class Solution:
    def isValid(self, s: str) -> bool: ...
```

Here `practice` calls a plain top-level function instead, with the same name and
argument and no `self`:

```python
def isValid(s: str) -> bool: ...
```

To try your answer on LeetCode, put the body inside the class method.

## Output

- Return the boolean `True` if the brackets are properly matched.
- Return the boolean `False` otherwise.
- It has to be a real `bool`. `1` and `0` are not accepted in their place.
- Every closing bracket needs an opener of its own kind before it, and no opener may
  be left open at the end.
- Counting is not enough: `"([)]"` has two of each kind and is still invalid, because
  the pairs cross.

## Constraints

These are the published bounds, read from the LeetCode problem page by this
project's tooling (see `readiness.json`).

- `1 <= len(s) <= 10_000`
- `s` consists only of the characters `()[]{}`.

## Examples (written for this project)

| `s` | Answer | Why |
| --- | --- | --- |
| `"[{}]"` | `True` | each pair closes inside the one around it |
| `"{[}]"` | `False` | `}` arrives while `[` is still open |
| `"(("` | `False` | two openers are never closed |
