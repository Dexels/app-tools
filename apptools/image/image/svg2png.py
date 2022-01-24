import cairosvg


def svg2png(filecontent, scale, path, size=None):
    encoding = 'UTF-8'
    bytestring = bytes(filecontent, encoding)

    if size is None:
        cairosvg.svg2png(bytestring=bytestring, write_to=path, scale=scale)
    else:
        try:
            cairosvg.svg2png(bytestring=bytestring, write_to=path, scale=scale, parent_width=float(size.split("x")[0]), parent_height=float(size.split("x")[1]))
        except:
            print('svg2png failed') 
