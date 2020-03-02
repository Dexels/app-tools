from os.path import basename, splitext


def file(image, extension='.png'):
    name = image.overwrite_name

    if image.overwrite_name is None:
        name, _ = splitext(image.basename)
        name = basename(name)

    if image.style is not None and image.include_style_name:
        name = name + '_' + image.style

    return name + extension
