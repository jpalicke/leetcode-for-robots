def containsDuplicate(nums):
    counts = {}
    for value in nums:
        counts[value] = counts.get(value, 0) + 1
    return any(count > 1 for count in counts.values())
