def isValid(s):
    expected = []
    for char in s:
        if char == "(":
            expected.append(")")
        elif char == "[":
            expected.append("]")
        elif char == "{":
            expected.append("}")
        elif not expected or expected.pop() != char:
            return False
    return not expected
