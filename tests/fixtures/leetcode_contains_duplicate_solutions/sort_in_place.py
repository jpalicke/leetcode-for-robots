def containsDuplicate(nums):
    nums.sort()
    return any(nums[i] == nums[i + 1] for i in range(len(nums) - 1))
