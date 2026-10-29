def search(nums, target):
    left, right = 0, len(nums) - 1
    while left <= right:
        mid = (left + right) // 2
        if nums[mid] > target:
            right = mid
        elif nums[mid] < target:
            left = mid
        else:
            return mid
    return -1
