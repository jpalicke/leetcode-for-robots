def maxProfit(prices):
    lowest = prices[0]
    best = 0
    for price in prices:
        if price < lowest:
            lowest = price
            best = 0
        best = max(best, price - lowest)
    return best
