# ABOUTME: Runner test fixture: a correct one-pass hash map Two Sum solution.
# ABOUTME: Intentionally outside the lint and type gates; run only by the tests.


def two_sum(nums, target):
    seen = {}
    for index, value in enumerate(nums):
        if target - value in seen:
            return [seen[target - value], index]
        seen[value] = index
