# Best Time to Buy and Sell Stock: correctness and complexity notes

Spoiler. Read this after you have tried the problem. It gives away every approach.

## Task in one line

Find the largest `prices[sell] - prices[buy]` with `sell` after `buy`, or `0` if every
such difference is negative or zero.

## Approaches

### 1. Brute force over all buy and sell pairs

For each buy day, try every later sell day and keep the largest difference, starting
the best at `0`.

- Correct because it examines every allowed pair once, so the best one is found.
- Time O(n^2), space O(1). With n up to 100,000 that is about five billion pairs,
  and no early exit is possible when the price only falls. It does not finish in time
  here, so the run is reported as a timeout, not a pass. A timeout shows the run did
  not finish; it does not prove the complexity.

### 2. One pass keeping the lowest price so far (the usual target)

Walk the days in order, remembering the lowest price seen on earlier days. On each day
the best sale you could make is `price - lowest`, so keep the largest of those, with
`0` as the starting best.

- Why it works: for any sale day, the best purchase is the cheapest earlier day, and
  the lowest price seen so far is exactly that. Taking the best over all sale days
  gives the best pair. Updating the lowest after (or together with) the comparison
  keeps the purchase on or before the sale day.
- Starting the best at `0` is what makes a falling list return `0`.
- Time O(n), space O(1).

### 3. Best change over a stretch of daily differences

Turn the prices into day-to-day changes. The best single trade is the best total over
any run of consecutive changes, which a running total that restarts when it goes
negative finds in one pass (the maximum subarray idea).

- Same complexity as approach 2. It is the same answer seen differently.

### 4. Right to left, keeping the highest price still ahead

Walk from the last day backwards remembering the highest price seen on later days. The
best purchase on a day is `highest_ahead - price`.

- A mirror image of approach 2; also O(n) time and O(1) space.

## Pitfalls

- Taking the highest price minus the lowest price in the whole list. The high may come
  before the low: `[8, 10, 1, 4]` gives `3`, not `9`.
- Taking the last price minus the first price. `[20, 6, 11, 1]` shows both that and the
  previous mistake are wrong.
- Fixing the purchase at the first day.
- Letting the best go negative. A falling list must return `0`.
- Forgetting to look at the last day as a sale day.
- Dropping the best profit when a new lowest price appears. `[1, 9, 0, 3]` must still
  return `8`.
- Failing on a list with one day.
- Returning `True`, `False` or `None`, or the day numbers, instead of the profit.

## Complexity summary

| Approach | Time | Extra space |
| --- | --- | --- |
| Brute force over pairs | O(n^2) | O(1) |
| One pass, lowest price so far | O(n) | O(1) |
| Daily differences, restarting total | O(n) | O(1) |
| Right to left, highest price ahead | O(n) | O(1) |
