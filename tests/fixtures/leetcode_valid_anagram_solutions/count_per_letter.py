import string


def isAnagram(s, t):
    return all(s.count(letter) == t.count(letter) for letter in string.ascii_lowercase)
