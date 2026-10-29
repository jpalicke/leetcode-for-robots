from typing import List


class Solution:
    def twoSum(self, nums: List[int], target: int) -> List[int]:
        prevMap = {}  # val -> index

        for i, n in enumerate(nums):
            diff = target - n
            if diff in prevMap:
                return [prevMap[diff], i]
            prevMap[n] = i


def twoSum(nums: List[int], target: int) -> List[int]:
    return Solution().twoSum(nums, target)
