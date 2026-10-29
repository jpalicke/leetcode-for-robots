def isValid(s):
    return all(s.count(o) == s.count(c) for o, c in ("()", "[]", "{}"))
