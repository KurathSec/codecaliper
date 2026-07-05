def dispatch(cmd, strict):
    match cmd:
        case 1:
            return "one"
        case 2:
            return "two"
        case _ if strict:  # note: the guard makes the wildcard a real branch
            return "guarded"
    return "other"


def label(tag):
    match tag:
        case "x":
            return 1
        case _:
            return 0
