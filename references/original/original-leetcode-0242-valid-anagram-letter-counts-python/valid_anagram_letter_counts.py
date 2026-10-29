def isAnagram(s: str, t: str) -> bool:
    """Count the letters of s up, the letters of t down, and expect all zeros."""
    if len(s) != len(t):
        return False
    counts = [0] * 26
    for letter in s:
        counts[ord(letter) - ord("a")] += 1
    for letter in t:
        counts[ord(letter) - ord("a")] -= 1
    return not any(counts)
