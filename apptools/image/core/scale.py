from apptools.image.core.json import json_get


class Scale(object):
    def __init__(self, multiplier, directory):
        self.multiplier = multiplier
        self.directory = directory

    @classmethod
    def load_from_json(cls, json):
        multiplier = float(json_get('multiplier', json))
        directory = json_get('directory', json, False)

        return cls(multiplier, directory)
