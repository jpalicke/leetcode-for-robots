def twoSum(nums, target):
    ordered = sorted((value, i) for i, value in enumerate(nums))
    left, right = 0, len(ordered) - 1
    while left < right:
        total = ordered[left][0] + ordered[right][0]
        if total == target:
            return [ordered[left][1], ordered[right][1]]
        if total < target:
            left += 1
        else:
            right -= 1
    raise ValueError("no pair")
