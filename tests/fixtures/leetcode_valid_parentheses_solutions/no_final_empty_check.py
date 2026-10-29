def isValid(s):
    stack = []
    for char in s:
        if char in "([{":
            stack.append(char)
        elif stack and {")": "(", "]": "[", "}": "{"}[char] == stack[-1]:
            stack.pop()
        else:
            return False
    return True
