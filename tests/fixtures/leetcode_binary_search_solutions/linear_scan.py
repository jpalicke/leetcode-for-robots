def search(nums, target):
    for index, value in enumerate(nums):
        if value == target:
            return index
    return -1
