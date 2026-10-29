def isValid(s):
    stack = []
    for char in s:
        if char in "([{":
            stack.append(char)
        elif {")": "(", "]": "[", "}": "{"}[char] == stack.pop():
            continue
        else:
            return False
    return not stack
