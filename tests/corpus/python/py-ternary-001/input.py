# plain ternary, then a nested ternary in the return's else arm
def pick(p, q, a, b, c):
    x = a if p else b
    return x if q else (b if p else c)
