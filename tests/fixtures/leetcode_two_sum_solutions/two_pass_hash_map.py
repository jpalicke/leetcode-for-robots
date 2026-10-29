def twoSum(nums, target):
    last = {value: i for i, value in enumerate(nums)}
    for i, value in enumerate(nums):
        j = last.get(target - value)
        if j is not None and j != i:
            return [i, j]
    raise ValueError("no pair")
