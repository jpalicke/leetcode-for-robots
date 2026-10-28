# ABOUTME: Runner test fixture: a correct Two Sum that prints to stdout and stderr.
# ABOUTME: Proves learner output cannot corrupt the runner's results.

import sys


def two_sum(nums, target):
    print("debug output from the learner")
    print("more debug output", file=sys.stderr)
    seen = {}
    for index, value in enumerate(nums):
        if target - value in seen:
            return [seen[target - value], index]
        seen[value] = index
