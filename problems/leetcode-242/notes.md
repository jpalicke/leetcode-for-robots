# Valid Anagram: correctness and complexity notes

Spoiler. Read this after you have tried the problem. It gives away every approach.

## Task in one line

Decide whether two strings hold the same letters with the same counts. Answer with a
real `bool`.

## Approaches

### 1. Sorting both strings

Sort the letters of `s` and of `t` and compare the results. Two strings are anagrams
exactly when their sorted forms are equal.

- Correct because sorting puts the letters in one canonical order, so strings with
  the same letters and counts give the same sequence, and any difference in letters
  or counts gives a different one.
- Time O(n log n), space O(n) for the sorted copies. Simple and hard to get wrong.

### 2. Letter counts (the usual target)

Count how many times each letter appears in `s`, then walk `t` and subtract. If a
count would go below zero, or the lengths differ, the answer is `False`. With equal
lengths and no count below zero, every count ends at zero.

- Why it works: equal lengths mean the total number of letters is the same, so if
  `t` never uses a letter more often than `s` supplies it, it must use every letter
  exactly as often.
- Time O(n), space O(1) for 26 letters (O(k) for an alphabet of k symbols).
- Two arrays of 26 counts and one dictionary of counts are the same idea.

### 3. Compare two count tables

Build a count table for each string and compare the tables. Same complexity as the
subtract version, one more table in memory.

## Pitfalls

- Comparing only which letters appear (`set(s) == set(t)`). `"aab"` and `"abb"`
  fool it.
- Comparing only the lengths.
- Comparing the sum of the letter codes. `"ad"` and `"bc"` have the same total and are
  not anagrams.
- Skipping the length check and then comparing only as far as the shorter string.
- Dropping the last or first letter from the comparison.
- Returning `1` or `0`, or `None`, instead of `True` or `False`.
- Assuming 26 letters when the input could hold other characters. For the stated
  lowercase input it is safe. The page's follow-up asks about Unicode: then a
  fixed 26-slot table no longer fits, and a dictionary of counts keyed by character
  (or sorting) is the natural adaptation. Take care that user-visible characters can
  be built from several code points, so decide whether to compare as given or after
  normalising. These tests do not cover this.

## Complexity summary

| Approach | Time | Extra space |
| --- | --- | --- |
| Sort both and compare | O(n log n) | O(n) |
| Count and subtract | O(n) | O(1) for 26 letters |
| Two count tables | O(n) | O(1) for 26 letters |

Note: at the size limit here, a slower but correct quadratic method still finishes in
time, so these tests do not tell a sorting answer from a counting one by speed.
