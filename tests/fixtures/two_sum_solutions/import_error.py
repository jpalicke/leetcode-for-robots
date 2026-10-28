# ABOUTME: Runner test fixture: a Two Sum module that fails while being imported.
# ABOUTME: Must be reported as an error in the import phase.

import module_that_does_not_exist  # noqa: F401


def two_sum(nums, target):
    return [0, 1]
