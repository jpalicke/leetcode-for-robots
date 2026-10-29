def search(nums, target):
    def look(left, right):
        if left > right:
            return -1
        mid = (left + right) // 2
        if nums[mid] == target:
            return mid
        if nums[mid] < target:
            return look(mid + 1, right)
        return look(left, mid - 1)

    return look(0, len(nums) - 1)
