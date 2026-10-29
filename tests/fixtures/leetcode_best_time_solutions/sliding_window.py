def maxProfit(prices):
    buy, best = 0, 0
    for sell in range(1, len(prices)):
        if prices[sell] < prices[buy]:
            buy = sell
        else:
            best = max(best, prices[sell] - prices[buy])
    return best
