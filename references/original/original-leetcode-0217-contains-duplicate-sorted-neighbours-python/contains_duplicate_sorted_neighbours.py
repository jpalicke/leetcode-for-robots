def containsDuplicate(nums: list[int]) -> bool:
    """Sort a copy, then look for two equal neighbours."""
    ordered = sorted(nums)
    return any(a == b for a, b in zip(ordered, ordered[1:], strict=False))
