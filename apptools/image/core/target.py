from apptools.image.core.json import json_get


class Target(object):
    def __init__(self, name, assets):
        self.name = name
        self.assets = assets

    @classmethod
    def load_from_json(cls, json):
        name = json_get('name', json)

        return cls(name, json_get('assets', json, False, ""))
