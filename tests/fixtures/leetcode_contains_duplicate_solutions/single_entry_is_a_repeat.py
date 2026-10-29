def containsDuplicate(nums):
    return len(nums) < 2 or len(set(nums)) != len(nums)
