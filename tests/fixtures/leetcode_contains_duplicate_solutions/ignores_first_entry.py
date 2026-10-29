def containsDuplicate(nums):
    return len(set(nums[1:])) != len(nums[1:])
