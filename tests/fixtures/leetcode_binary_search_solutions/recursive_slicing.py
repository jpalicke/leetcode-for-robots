def search(nums, target):
    def look(part, offset):
        if not part:
            return -1
        mid = len(part) // 2
        if part[mid] == target:
            return offset + mid
        if part[mid] < target:
            return look(part[mid + 1 :], offset + mid + 1)
        return look(part[:mid], offset)

    return look(nums, 0)
