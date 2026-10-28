# ABOUTME: Runner test fixture: a correct brute force Two Sum, reversed index order.
# ABOUTME: Proves a different valid algorithm and answer order is accepted.


def two_sum(nums, target):
    for first in range(len(nums)):
        for second in range(first + 1, len(nums)):
            if nums[first] + nums[second] == target:
                return [second, first]
