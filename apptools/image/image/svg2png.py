import cairosvg


def svg2png(filecontent, scale, path, size=None):
    encoding = 'UTF-8'
    bytestring = bytes(filecontent, encoding)

    if size is None:
        cairosvg.svg2png(bytestring=bytestring, write_to=path, scale=scale)
    else:
        cairosvg.svg2png(bytestring=bytestring,
                         write_to=path,
                         scale=scale,
                         parent_height=size.height,
                         parent_width=size.width)
