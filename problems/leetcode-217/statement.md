# 217. Contains Duplicate (Easy)

Original problem: <https://leetcode.com/problems/contains-duplicate/>. This page is
our own short summary, not the platform's text. Read the original for its exact
wording.

## Task

You get a list of integers `nums`. Say whether any value shows up in the list more
than once.

## What you write

LeetCode asks for a method on a class:

```python
class Solution:
    def containsDuplicate(self, nums: list[int]) -> bool: ...
```

Here `practice` calls a plain top-level function instead, with the same name and
argument and no `self`:

```python
def containsDuplicate(nums: list[int]) -> bool: ...
```

To try your answer on LeetCode, put the body inside the class method.

## Output

- Return the boolean `True` if at least one value appears two or more times.
- Return the boolean `False` if every value appears exactly once.
- It has to be a real `bool`. `1` and `0` are not accepted in their place.
- Compare values, not positions. Two entries are repeats when they hold equal
  numbers, wherever they sit in the list.
- `5` and `-5` are different values.

## Constraints

These are the bounds this project's tests are built to, taken from the published
problem. They have not been re-checked against the live page from this project's
tooling (see `readiness.json`).

- `1 <= len(nums) <= 100_000`
- `-1_000_000_000 <= nums[i] <= 1_000_000_000`

A list with one entry has no repeat, so the answer is `False`.

## Examples (written for this project)

| `nums` | Answer | Why |
| --- | --- | --- |
| `[5, 8, 2, 8]` | `True` | `8` appears twice |
| `[4, 9, 1, 7]` | `False` | every value is different |
| `[5, -5, 7, -7]` | `False` | `5` and `-5` are different values |
