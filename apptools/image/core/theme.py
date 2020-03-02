from apptools.image.core.colorset import Colorset
from apptools.image.core.json import json_get


class Theme(object):
    def __init__(self, name, default_colorset, custom_colorsets):
        self.name = name
        self.default_colorset = default_colorset
        self.custom_colorsets = custom_colorsets

    @classmethod
    def load_from_json(cls, json):
        name = json_get('name', json)

        custom_colorsets = {}
        for custom_colorset in json_get('custom_colorsets', json):
            colorset_name = custom_colorset['name']
            colorset = Colorset(custom_colorset['colorset'])

            custom_colorsets[colorset_name] = colorset

        return cls(name, Colorset(json_get('default_colorset', json)),
                   custom_colorsets)

    def get(self, key):
        for theme_name, colorset in self.custom_colorsets.items():
            if key == theme_name:
                return colorset
        return self.default_colorset
