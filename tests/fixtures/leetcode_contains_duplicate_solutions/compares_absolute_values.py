def containsDuplicate(nums):
    return len({abs(value) for value in nums}) != len(nums)
