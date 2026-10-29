def twoSum(nums: list[int], target: int) -> list[int]:
    """Sort (value, position) pairs, then close in from both ends."""
    ordered = sorted((value, position) for position, value in enumerate(nums))
    left, right = 0, len(ordered) - 1
    while left < right:
        total = ordered[left][0] + ordered[right][0]
        if total == target:
            return [ordered[left][1], ordered[right][1]]
        if total < target:
            left += 1
        else:
            right -= 1
    raise ValueError("no pair adds up to the target")
