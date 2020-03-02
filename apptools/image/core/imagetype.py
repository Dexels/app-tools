from enum import Enum, unique

from apptools.image.core.json import json_get


@unique
class ImageType(Enum):
    IMAGE = 1
    APPICON = 2

    def __str__(self):
        return self.name.lower()

    def to_set(self):
        return "%sset" % self

    @classmethod
    def load_from_json(cls, json):
        raw_type = json_get('type', json, False, 'IMAGE')
        return ImageType[raw_type.upper()]
