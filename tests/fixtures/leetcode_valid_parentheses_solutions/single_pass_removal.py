def isValid(s):
    return s.replace("()", "").replace("[]", "").replace("{}", "") == ""
