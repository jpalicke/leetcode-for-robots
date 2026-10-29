def maxProfit(prices):
    lowest = prices[0]
    best = 0
    for price in prices[:-1]:
        lowest = min(lowest, price)
        best = max(best, price - lowest)
    return best
