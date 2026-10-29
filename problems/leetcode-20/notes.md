# Valid Parentheses: correctness and complexity notes

Spoiler. Read this after you have tried the problem. It gives away every approach.

## Task in one line

Decide whether every bracket is closed by its own kind, in the right order. Answer
with a real `bool`.

## Approaches

### 1. A stack of open brackets (the usual target)

Walk the string once, keeping a stack of the opening brackets that are still open.
For an opener, push it. For a closer, the top of the stack must be its matching
opener: if the stack is empty or the top is a different kind, return `False`;
otherwise pop it. After the walk the answer is whether the stack is empty.

- Why it works: brackets must close in the reverse of the order they opened, which
  is exactly last in, first out. The most recent unclosed opener is the only one a
  closer is allowed to match, and the stack always has it on top.
- The final emptiness check matters: a string that never mismatches can still leave
  openers behind.
- Time O(n), space O(n) in the worst case (all openers).

### 2. Repeated removal of adjacent pairs

Delete every adjacent `()`, `[]` and `{}` and repeat until nothing more can be
deleted. The string is valid exactly when nothing is left.

- Correct because in a valid string some pair is always directly adjacent (the
  innermost one), and removing it leaves a smaller valid string; in an invalid string
  removal gets stuck with something left over.
- Each pass is O(n) and a deeply nested string needs about n/2 passes, so the worst
  case is O(n^2) time. At n up to 10,000 it still finishes quickly here, so these
  tests do not tell it from the stack by speed.
- A single pass of removal is not enough. It fixes `"()[]{}"` but not `"([{}])"`.

## Pitfalls

- Counting the openers and closers of each kind. `"([)]"` and `")("` balance on counts
  and are invalid.
- Matching any closer to any opener, so `"(]"` is accepted.
- Forgetting the final check that nothing is left open, so `"("` is accepted.
- Popping from an empty stack when the string starts with a closer (`")"`).
- Treating only fully nested strings as valid, so `"()[]{}"` is rejected.
- Returning `1` or `0`, or `None`, instead of `True` or `False`.
- Checking only that the length is even.

## Complexity summary

| Approach | Time | Extra space |
| --- | --- | --- |
| Stack of open brackets | O(n) | O(n) |
| Repeated removal of pairs | O(n^2) worst case | O(n) |
