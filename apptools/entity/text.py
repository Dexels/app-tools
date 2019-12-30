def capitalize(s: str) -> str:
    if len(s) <= 1:
        return s.upper()

    return s[0].upper() + s[1:]


def camelcase(s: str) -> str:
    if len(s) <= 1:
        return s.lower()
    return s[0].lower() + s[1:]
