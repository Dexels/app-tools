import os

from apptools.image.core.image import Image
from apptools.image.core.json import json_get
from apptools.image.core.platform import Platform
from apptools.image.core.theme import Theme


class Spec(object):
    def __init__(self, shared_path, project, platforms, images,
                 placeholder_colormap, themes):
        self.shared_path = os.path.expanduser(shared_path)
        self.project = project
        self.platforms = platforms
        self.images = images
        self.placeholder_colormap = placeholder_colormap
        self.themes = themes

    @classmethod
    def load_from_json(cls, json):
        project = json_get('project', json)

        shared_path = os.path.join("~/git/", json_get('shared', json))

        return cls(shared_path, project, [
            Platform.load_from_json(platform, project)
            for platform in json_get('platforms', json)
        ], [Image.load_from_json(image) for image in json_get('images', json)],
                   json_get('placeholder_colormap', json), [
                       Theme.load_from_json(theme)
                       for theme in json_get('themes', json)
                   ])
