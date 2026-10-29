from itertools import accumulate


def maxProfit(prices):
    return max(price - low for price, low in zip(prices, accumulate(prices, min)))
