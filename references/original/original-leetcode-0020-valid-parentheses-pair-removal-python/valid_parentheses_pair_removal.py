def isValid(s: str) -> bool:
    """Delete adjacent matching pairs until none are left; valid if nothing remains."""
    while True:
        shorter = s.replace("()", "").replace("[]", "").replace("{}", "")
        if shorter == s:
            return s == ""
        s = shorter
