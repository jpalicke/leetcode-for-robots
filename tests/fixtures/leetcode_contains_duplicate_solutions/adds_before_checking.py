def containsDuplicate(nums):
    seen = set()
    for value in nums:
        seen.add(value)
        if value in seen:
            return True
    return False
