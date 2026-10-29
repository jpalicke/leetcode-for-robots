def maxProfit(prices):
    prices = prices[1:] or [0]
    lowest = prices[0]
    best = 0
    for price in prices:
        lowest = min(lowest, price)
        best = max(best, price - lowest)
    return best
