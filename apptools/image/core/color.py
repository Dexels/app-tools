def hex_to_rgba(hex):
    hex = hex.lstrip('#')

    a = 1
    r = 1
    g = 1
    b = 1

    if len(hex) > 6:
        a = 1 / 255 * int(hex[0:2], 16)
        r = int(hex[2:4], 16)
        g = int(hex[4:6], 16)
        b = int(hex[6:8], 16)
    else:
        r = int(hex[0:2], 16)
        g = int(hex[2:4], 16)
        b = int(hex[4:6], 16)

    return (r, g, b, a)
