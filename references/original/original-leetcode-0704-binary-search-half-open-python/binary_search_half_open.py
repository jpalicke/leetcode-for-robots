def search(nums: list[int], target: int) -> int:
    """Search the half-open window [low, high); each step drops the probe."""
    low, high = 0, len(nums)
    while low < high:
        probe = (low + high) // 2
        if nums[probe] < target:
            low = probe + 1
        elif nums[probe] > target:
            high = probe
        else:
            return probe
    return -1
