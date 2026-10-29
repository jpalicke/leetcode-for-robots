def maxProfit(prices):
    return max(0, max(price - prices[0] for price in prices))
