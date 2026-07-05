def parse_count(raw):
    try:
        return int(raw)
    except ValueError:
        return None
    except Exception:
        raise
