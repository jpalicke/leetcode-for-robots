def twoSum(nums, target):
    seen = {}
    for i, value in enumerate(nums):
        if value <= 0:
            continue
        if target - value in seen:
            return [seen[target - value], i]
        seen[value] = i
    return [0, 1]
