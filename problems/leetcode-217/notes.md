# Contains Duplicate: correctness and complexity notes

Spoiler. Read this after you have tried the problem. It gives away every approach.

## Task in one line

Decide whether any value occurs at least twice. Answer with a real `bool`.

## Approaches

### 1. Brute force over all pairs

For each position `i`, compare `nums[i]` with every later entry. Return `True` at the
first equal pair and `False` after every pair has been looked at.

- Correct because it examines every unordered pair of positions once, so a repeated
  value is found if one exists.
- Time O(n^2), space O(1). With n up to 100,000 that is about five billion
  comparisons. It stops early when a repeat is near the front, but a list with no
  repeat has to be searched in full, so it times out here. That is the point of the
  larger cases: a correct quadratic answer is reported as a timeout, not a pass, and
  a timeout does not prove the complexity, only that the run did not finish.

### 2. Hash set, one pass (the usual target)

Walk the list once, keeping a hash set of the values already seen. If the current
value is in the set, return `True`. Otherwise add it and continue. Return `False`
after the walk.

- Why it works: if a value occurs twice, the walk reaches its second copy after the
  first is stored, so the check fires. A hit always means two entries hold the same
  value, so it never fires wrongly.
- Time O(n) on average (each lookup and insert is O(1) on average), space O(n).
- The check comes before the insert. Inserting first would make every value find
  itself.

### 3. Compare lengths

Build a set from the whole list and compare its size with the length of the list.
The two differ exactly when something was dropped as a repeat.

- Same complexity as the loop, shorter to write. It cannot stop early, so it always
  does the full pass.

### 4. Sort, then compare neighbours

Sort a copy of the list. Equal values end up next to each other, so scan once for
two neighbours that are equal.

- Correct because after sorting, any two equal values are adjacent (or separated only
  by further copies of the same value).
- Time O(n log n) for the sort, space O(n) for the copy (or O(1) extra when sorting
  the input in place, which changes the caller's list).

## Pitfalls

- Returning a count, `1` or `0`, or `None` instead of `True` or `False`.
- Checking only neighbours in the original, unsorted order. `[1, 2, 1]` has a repeat
  that is not next to its twin.
- Stopping the loop one entry early so the last value is never compared.
- Treating `5` and `-5` as the same value, for example by comparing absolute values.
- Treating a single-entry list as a repeat, or failing on it.
- Putting the value into the set before checking for it.
- Sorting the caller's list in place without saying so.

## Complexity summary

| Approach | Time | Extra space |
| --- | --- | --- |
| Brute force | O(n^2) | O(1) |
| Hash set, one pass | O(n) average | O(n) |
| Compare set size to length | O(n) average | O(n) |
| Sort and compare neighbours | O(n log n) | O(n) |
