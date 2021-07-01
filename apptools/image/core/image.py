from apptools.image.core.imagetype import ImageType
from apptools.image.core.json import json_get


class Image(object):
    def __init__(self, basename, type, targets, style, platforms, colorize,
                 size, include_style_name, overwrite_name):
        self.basename = basename
        self.type = type
        self.targets = targets
        self.style = style
        self.platforms = platforms
        self.colorize = colorize
        self.size = size
        self.include_style_name = include_style_name
        self.overwrite_name = overwrite_name

    def isSVG(self):
        return self.basename.endswith(".svg")

    def isPNG(self):
        return self.basename.endswith(".png")

    @classmethod
    def load_from_json(cls, json):
        basename = json_get('basename', json)

        return cls(basename, ImageType.load_from_json(json),
                   json_get('targets', json, False),
                   json_get('style', json, False),
                   json_get('platforms', json, False),
                   json_get('colorize', json, False, True),
                   json_get('size', json, False),
                   json_get('include_style_name', json, False, True),
                   json_get('overwrite_name', json, False))
