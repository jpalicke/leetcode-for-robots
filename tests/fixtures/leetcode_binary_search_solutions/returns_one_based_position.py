def search(nums, target):
    for index, value in enumerate(nums):
        if value == target:
            return index + 1
    return -1
