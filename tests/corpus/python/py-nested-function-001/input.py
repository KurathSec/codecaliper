def outer(items):
    def inner(x):
        if x:
            return 1
        return 0
    total = 0
    for it in items:
        if inner(it):
            total += 1
    return total
