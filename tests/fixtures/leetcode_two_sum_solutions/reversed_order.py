def twoSum(nums, target):
    seen = {}
    for i in range(len(nums) - 1, -1, -1):
        if target - nums[i] in seen:
            return [i, seen[target - nums[i]]]
        seen[nums[i]] = i
    raise ValueError("no pair")
