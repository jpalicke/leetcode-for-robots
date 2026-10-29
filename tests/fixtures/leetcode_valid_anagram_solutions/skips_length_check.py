def isAnagram(s, t):
    return all(a == b for a, b in zip(sorted(s), sorted(t)))
