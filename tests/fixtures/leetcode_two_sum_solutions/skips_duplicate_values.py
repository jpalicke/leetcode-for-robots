def twoSum(nums, target):
    seen = {}
    for i, value in enumerate(nums):
        if value in seen:
            continue
        seen[value] = i
        partner = target - value
        if partner in seen and seen[partner] != i:
            return [seen[partner], i]
    return [-1, -1]
