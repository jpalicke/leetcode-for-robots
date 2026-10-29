from bisect import bisect_left


def search(nums, target):
    spot = bisect_left(nums, target)
    return spot if spot < len(nums) and nums[spot] == target else -1
