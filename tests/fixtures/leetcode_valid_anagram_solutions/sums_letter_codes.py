def isAnagram(s, t):
    return sum(map(ord, s)) == sum(map(ord, t))
