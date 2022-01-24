from os.path import expanduser

from apptools.image.core.json import json_get
from apptools.image.core.scale import Scale
from apptools.image.core.target import Target


class Platform(object):
    def __init__(self, name, path, scales, targets, attributes,
                 is_default_platform):
        self.name = name
        self.path = expanduser(path)
        self.scales = scales
        self.targets = targets
        self.attributes = attributes
        self.is_default_platform = is_default_platform

    def is_android(self):
        return self.name.startswith("android")

    def is_ios(self):
        return self.name == "ios"

    def is_scp(self):
        return self.name == "scp"

    @classmethod
    def load_from_json(cls, json, project):
        name = json_get('name', json)
        repository = json_get('repository', json)

        path = "../%s" % repository

        return cls(name, path, [
            Scale.load_from_json(scale) for scale in json_get('scales', json)
        ], [
            Target.load_from_json(target)
            for target in json_get('targets', json)
        ], json_get('attributes', json, False, []),
                   json_get('is_default_platform', json, False, True))

    def get_target(self, name):
        for target in self.targets:
            if target.name == name:
                return target
        raise KeyError

    def __repr__(self):
        return 'Platform({})'.format(self.name)
