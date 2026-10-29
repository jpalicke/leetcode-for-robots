# 1. Two Sum (Easy)

Original problem: <https://leetcode.com/problems/two-sum/>. This page is our own
short summary, not the platform's text. Read the original for its exact wording.

## Task

You get a list of integers `nums` and an integer `target`. Exactly one pair of
different positions in the list holds values that add up to `target`. Return those
two positions.

## What you write

LeetCode asks for a method on a class:

```python
class Solution:
    def twoSum(self, nums: list[int], target: int) -> list[int]: ...
```

Here `practice` calls a plain top-level function instead, with the same name and
arguments and no `self`:

```python
def twoSum(nums: list[int], target: int) -> list[int]: ...
```

To try your answer on LeetCode, put the body inside the class method.

## Output

- A list of exactly two integers: the two positions (indices, counting from 0).
- The two positions must be different. One entry cannot be used twice, but two
  entries that hold equal values are fine.
- Either order is accepted. `[1, 3]` and `[3, 1]` are the same answer.
- Return indices, not the values.

## Constraints

- `2 <= len(nums) <= 10_000`
- `-1_000_000_000 <= nums[i] <= 1_000_000_000`
- `-1_000_000_000 <= target <= 1_000_000_000`
- Exactly one valid pair exists, so you never need to handle "no answer".

## Examples (written for this project)

| `nums` | `target` | An accepted answer | Why |
| --- | --- | --- | --- |
| `[1, 4, 6, 9]` | `13` | `[1, 3]` | `4 + 9 == 13` |
| `[8, 3, 5, 1]` | `6` | `[2, 3]` | `5 + 1 == 6` |
| `[3, 3]` | `6` | `[0, 1]` | equal values at two positions |
