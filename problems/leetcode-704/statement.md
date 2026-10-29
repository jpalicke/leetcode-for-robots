# 704. Binary Search (Easy)

Original problem: <https://leetcode.com/problems/binary-search/>. This page is our
own short summary, not the platform's text. Read the original for its exact wording.

## Task

You get a list of integers `nums` that is already sorted from smallest to largest,
and an integer `target`. If `target` is in the list, return its position. If it is
not, return `-1`.

## What you write

LeetCode asks for a method on a class:

```python
class Solution:
    def search(self, nums: list[int], target: int) -> int: ...
```

Here `practice` calls a plain top-level function instead, with the same name and
arguments and no `self`:

```python
def search(nums: list[int], target: int) -> int: ...
```

To try your answer on LeetCode, put the body inside the class method.

## Output

- Return the index (counting from 0) of `target` in `nums`.
- Return `-1` when `target` does not appear.
- Every value in `nums` is different, so there is never more than one right answer.
- The result has to be an integer. `None`, a boolean or the value itself are wrong.

## Constraints

These are the published bounds, read from the LeetCode problem page by this
project's tooling (see `readiness.json`).

- `1 <= len(nums) <= 10_000`
- `-10_000 < nums[i], target < 10_000` (so `-9_999` to `9_999`, both ends inclusive)
- all values in `nums` are different
- `nums` is sorted in ascending order

## Running time

The problem asks for an algorithm that runs in `O(log n)` time. `practice` checks this
by counting how many different entries of `nums` your function looks at. A search that
halves the range reads about 14 of 10,000 entries, and a run allows 16. A scan that
reads most of the list fails with the count it reached, even when its answer is right.
Copying the list or slicing it counts every entry copied, and so does `in`,
`.index()`, `sum()` and any loop over the whole list. This is a check on what your
code reads, not a proof of its running time. See `notes.md` for what the requirement
means after you have tried.

## Examples (written for this project)

| `nums` | `target` | Answer | Why |
| --- | --- | --- | --- |
| `[2, 4, 6, 8, 10]` | `8` | `3` | `8` is at index 3 |
| `[2, 4, 6, 8, 10]` | `5` | `-1` | `5` is not in the list |
| `[7]` | `7` | `0` | a one-entry list can hold the target |
