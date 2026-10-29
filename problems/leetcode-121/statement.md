# 121. Best Time to Buy and Sell Stock (Easy)

Original problem: <https://leetcode.com/problems/best-time-to-buy-and-sell-stock/>.
This page is our own short summary, not the platform's text. Read the original for its
exact wording.

## Task

You get a list `prices` where `prices[i]` is a stock's price on day `i`. You may make
one purchase on one day and one sale on a later day. Return the largest profit you can
make. If no purchase and sale can make a profit, return `0`.

## What you write

LeetCode asks for a method on a class:

```python
class Solution:
    def maxProfit(self, prices: list[int]) -> int: ...
```

Here `practice` calls a plain top-level function instead, with the same name and
argument and no `self`:

```python
def maxProfit(prices: list[int]) -> int: ...
```

To try your answer on LeetCode, put the body inside the class method.

## Output

- Return an integer: the profit, which is the sale price minus the purchase price.
- The sale has to come on a later day than the purchase. Buying on a high day and
  selling on an earlier, lower day does not count.
- If every possible sale loses money or breaks even, return `0`, never a negative
  number.
- You buy once and sell once. You do not have to buy on the first day or sell on the
  last.

## Constraints

These are the published bounds, read from the LeetCode problem page by this
project's tooling (see `readiness.json`).

- `1 <= len(prices) <= 100_000`
- `0 <= prices[i] <= 10_000`

A list with a single day has no later day to sell on, so the answer is `0`.

## Examples (written for this project)

| `prices` | Answer | Why |
| --- | --- | --- |
| `[2, 7, 1, 5]` | `5` | buy at `2`, sell at `7` |
| `[5, 4, 3]` | `0` | the price only falls, so no trade helps |
| `[9, 1, 4]` | `3` | buy at `1`, sell at `4`; the `9` is before the low |
