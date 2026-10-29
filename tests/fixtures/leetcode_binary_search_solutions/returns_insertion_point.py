from bisect import bisect_left


def search(nums, target):
    return bisect_left(nums, target)
