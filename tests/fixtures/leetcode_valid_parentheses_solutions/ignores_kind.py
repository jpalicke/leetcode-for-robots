def isValid(s):
    depth = 0
    for char in s:
        depth += 1 if char in "([{" else -1
        if depth < 0:
            return False
    return depth == 0
