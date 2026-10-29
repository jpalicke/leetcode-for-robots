def maxProfit(prices):
    best = running = 0
    for today, tomorrow in zip(prices, prices[1:]):
        running = max(0, running + tomorrow - today)
        best = max(best, running)
    return best
