def maxProfit(prices):
    best = -10**9
    lowest = prices[0]
    for price in prices[1:]:
        best = max(best, price - lowest)
        lowest = min(lowest, price)
    return best
