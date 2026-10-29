def isValid(s):
    stack = []
    for char in s:
        if char in "([{":
            stack.append(char)
        elif not stack or {")": "(", "]": "[", "}": "{"}[char] != stack.pop():
            return 0
    return 0 if stack else 1
