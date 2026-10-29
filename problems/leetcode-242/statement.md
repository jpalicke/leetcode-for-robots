# 242. Valid Anagram (Easy)

Original problem: <https://leetcode.com/problems/valid-anagram/>. This page is our
own short summary, not the platform's text. Read the original for its exact wording.

## Task

You get two strings, `s` and `t`. Say whether `t` is an anagram of `s`: it must use
exactly the same letters as `s`, each one the same number of times, in any order.

## What you write

LeetCode asks for a method on a class:

```python
class Solution:
    def isAnagram(self, s: str, t: str) -> bool: ...
```

Here `practice` calls a plain top-level function instead, with the same name and
arguments and no `self`:

```python
def isAnagram(s: str, t: str) -> bool: ...
```

To try your answer on LeetCode, put the body inside the class method.

## Output

- Return the boolean `True` if `t` is an anagram of `s`.
- Return the boolean `False` otherwise.
- It has to be a real `bool`. `1` and `0` are not accepted in their place.
- Order does not matter, but counts do: `"aab"` and `"abb"` use the same kinds of
  letters and are still not anagrams.
- Strings of different lengths can never be anagrams.

## Constraints

PENDING: confirm against the problem page before this package is marked ready.

- `1 <= len(s), len(t) <= 50_000`
- `s` and `t` hold only lowercase English letters (`a` to `z`).

## Examples (written for this project)

| `s` | `t` | Answer | Why |
| --- | --- | --- | --- |
| `"listen"` | `"silent"` | `True` | the same six letters, rearranged |
| `"stone"` | `"stoke"` | `False` | `n` against `k` |
| `"aab"` | `"abb"` | `False` | same letters, different counts |
