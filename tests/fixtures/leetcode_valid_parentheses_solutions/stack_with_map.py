def isValid(s):
    opener_of = {")": "(", "]": "[", "}": "{"}
    stack = []
    for char in s:
        if char in opener_of:
            if not stack or stack.pop() != opener_of[char]:
                return False
        else:
            stack.append(char)
    return not stack
