def maxProfit(prices):
    best = 0
    highest = prices[-1]
    for price in reversed(prices):
        highest = max(highest, price)
        best = max(best, highest - price)
    return best
