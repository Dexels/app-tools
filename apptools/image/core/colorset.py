class Colorset(object):
    def __init__(self, color):
        self._color = color

        if isinstance(self._color, dict):
            for key, value in color.items():
                setattr(self, key, value)

    @classmethod
    def load_from_json(cls, json):
        return cls(json)

    def get(self, key):
        if getattr(self, key) is not None:
            return getattr(self, key)

        return self._color
