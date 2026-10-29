def twoSum(nums, target):
    seen = {}
    for i, value in enumerate(nums):
        if target - value in seen:
            return [i, seen[target - value]]
        seen[value] = i
    raise ValueError("no pair")
