class Colorset(object):
    def __init__(self, color):
        self._color = color

    @classmethod
    def load_from_json(cls, json):
        return cls(json)

    def get(self, key):
        if self._color == None:
            return None

        if isinstance(self._color, dict):
            return self._color.get(key)
        return self._color
