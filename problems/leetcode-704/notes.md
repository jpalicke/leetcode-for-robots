# Binary Search: correctness and complexity notes

Spoiler. Read this after you have tried the problem. It gives away every approach.

## Task in one line

Find a value in a sorted list of different integers and return its index, or `-1`.

## Approaches

### 1. Linear scan

Walk the list from the front and return the index of the first entry equal to
`target`; return `-1` if you reach the end.

- Correct because it looks at every entry, so it cannot miss the target.
- Time O(n), space O(1). It ignores the fact that the list is sorted.
- It gives the right answer but reads up to every entry, so `practice` rejects it
  under the `O(log n)` read budget and reports how many entries it looked at.
  `nums.index(target)` and `target in nums` are the same thing in one call.

### 2. Binary search (the usual target)

Keep a window of positions that could still hold `target`, starting with the whole
list. Look at the entry in the middle of the window. If it equals `target`, return its
position. If it is too small, the target can only be to its right, so move the left
edge past it. If it is too big, move the right edge before it. If the window becomes
empty, return `-1`.

- Why it works: the list is sorted, so one comparison rules out every entry on one
  side of the probe. The window always contains every position that could still hold
  the target, so it cannot lose it.
- It stops because every step either returns or shrinks the window by at least one
  entry (move past the probe, never onto it).
- Time O(log n): the window about halves each step. Space O(1) when written as a loop.
- Written with a closed window (`left <= right`, moves `mid + 1` and `mid - 1`) or a
  half-open window (`left < right`); both are right if the edges are kept consistent.

### 3. The library routine

`bisect.bisect_left` finds the position where `target` would be inserted. The answer
is that position if the entry there equals `target`, and `-1` otherwise (also `-1`
when the position is past the end).

## Pitfalls

- Looping while `left < right` with a closed window, which never examines a window of
  one entry. `[5]` with target `5` then returns `-1`.
- Moving an edge to `mid` instead of `mid + 1` or `mid - 1`, so the window stops
  shrinking and the loop never ends on a missing target.
- Setting the right edge to `len(nums)` with a closed window, which can read past the
  end.
- Starting the left edge at `1`, or the right edge at `len(nums) - 2`, which loses the
  first or last entry.
- Computing the probe with `/` instead of `//`; it gives a float and a list cannot be
  indexed with it.
- Returning the insertion point, or `0`, or `None`, for a missing target instead of `-1`.
- Returning the value found instead of its index.
- Searching only one side of the first probe.
- Recursing on slices (`nums[mid + 1:]`). The recursion depth is logarithmic, but each
  slice copies the part it keeps, which adds up to a linear amount of work. The read
  budget counts every copied entry, so it rejects this.
- Believing the budget is exact. Checking `nums[0]` and `nums[-1]` before the loop is
  fine; the limit leaves room for a couple of extra reads.

## Complexity summary

| Approach | Time | Extra space |
| --- | --- | --- |
| Linear scan | O(n) | O(1) |
| Binary search, loop | O(log n) | O(1) |
| Binary search, recursion | O(log n) | O(log n) for the call stack |
| `bisect_left` plus a check | O(log n) | O(1) |

Note: the local run counts the different entries your function reads. A halving
search reads about 14 of 10,000; a scan reads most of them. The count is evidence about
what your code read on these inputs, not a proof of its running time.
