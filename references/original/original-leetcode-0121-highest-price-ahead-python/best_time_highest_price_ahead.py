def maxProfit(prices: list[int]) -> int:
    """Walk from the last day back, remembering the highest price still ahead."""
    best = 0
    highest_ahead = prices[-1]
    for day in range(len(prices) - 2, -1, -1):
        best = max(best, highest_ahead - prices[day])
        highest_ahead = max(highest_ahead, prices[day])
    return best
