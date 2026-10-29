def isAnagram(s, t):
    if len(s) != len(t):
        return False
    counts = {}
    for letter in s:
        counts[letter] = counts.get(letter, 0) + 1
    for letter in t:
        if counts.get(letter, 0) == 0:
            return False
        counts[letter] -= 1
    return True
