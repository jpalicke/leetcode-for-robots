def containsDuplicate(nums):
    return any(value == nums[0] for value in nums[1:])
