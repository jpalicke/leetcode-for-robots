# Two Sum: correctness and complexity notes

Spoiler. Read this after you have tried the problem. It gives away every approach.

## Task in one line

Find the two different positions whose values add up to `target`. Exactly one pair
exists.

## Approaches

### 1. Brute force over all pairs

For each position `i`, try every later position `j` and test `nums[i] + nums[j]`.

- Correct because it examines every unordered pair of positions once, so the unique
  valid pair is found.
- Time O(n^2), space O(1). With n up to 10,000 that is about 50 million pair checks.
  It finishes in a few seconds in CPython. This suite accepts it, and the run time
  shows in the report. Correct and slower is a complete local result.

### 2. One pass with a hash map (the usual target)

Walk the list once, keeping a map from value to position for entries already seen.
For the entry at `i`, the partner value is `target - nums[i]`. If the map holds it,
the answer is `[map[partner], i]`. Otherwise store `nums[i] -> i` and continue.

- Why it works: the valid pair has a smaller position `a` and a larger position
  `b`. When the walk reaches `b`, the entry at `a` is already stored, so the lookup
  succeeds. Nothing earlier can fire a wrong answer, because a hit means a stored
  value plus the current value equals `target`, and the stored entry has a different,
  earlier position.
- Time O(n) on average (each lookup and insert is O(1) on average), space O(n).
- The check comes before the insert. That order is what stops one entry from pairing
  with itself.

### 3. Two passes with a hash map

First build `value -> position` for the whole list, then look up each partner. A
repeated value keeps only its last position, so you must reject a hit whose position
equals the current one. It is the same complexity with one more thing to get wrong.

### 4. Sort and two pointers, tracking original positions

Sort pairs of `(value, original_position)`. Move a left pointer from the start and a
right pointer from the end: if the sum is too small advance left, if too large
retreat right, otherwise return the two original positions.

- Correct because for sorted values a sum that is too small cannot be repaired by
  any pairing that uses the left value with something at or left of the right
  pointer, so the left pointer can safely move (and symmetrically for the right).
- Time O(n log n) for the sort, space O(n) for the pairs. Sorting loses the original
  positions unless you carry them along; that is the main pitfall.

## Pitfalls

- Returning values instead of indices.
- Using the same entry twice, for example `target = 12` with a single `6` in the
  list. Equal values at two different positions (`[3, 3]` with target `6`) are a
  valid answer, so do not skip a value just because it was seen.
- Looking a value up with `list.index`: it always finds the first match, which turns
  `[3, 3]` into `[0, 0]` and hides an O(n) scan inside an O(n) loop.
- Off-by-one loop bounds that never reach the last position.
- Assuming all numbers are positive. Negative values and zero are in range, so do not
  discard a value because it is larger than `target`.
- Returning `None` when nothing is found. The problem promises an answer exists.

## Complexity summary

| Approach | Time | Extra space |
| --- | --- | --- |
| Brute force | O(n^2) | O(1) |
| Hash map, one pass | O(n) average | O(n) |
| Hash map, two passes | O(n) average | O(n) |
| Sort plus two pointers | O(n log n) | O(n) |
