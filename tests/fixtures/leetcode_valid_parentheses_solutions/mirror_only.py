def isValid(s):
    pair = {"(": ")", "[": "]", "{": "}"}
    half = len(s) // 2
    return len(s) % 2 == 0 and all(pair.get(s[i]) == s[-1 - i] for i in range(half))
