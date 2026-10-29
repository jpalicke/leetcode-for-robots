def isAnagram(s, t):
    return len(s) == len(t) and sorted(s[1:]) == sorted(t[1:])
