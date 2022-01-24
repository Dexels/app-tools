from enum import Enum, unique


@unique
class Idiom(Enum):
    IPAD = 1
    IPHONE = 2
    UNIVERSAL = 3
    MARKETING = 4

    def __str__(self):
        if self == Idiom.MARKETING:
            return "ios-marketing"
        return self.name.lower()


class ImageDefinition(object):
    def __init__(self, idiom, scale, size=None):
        self.idiom = idiom
        self.scale = scale
        self.size = size

    def filename(self, imagename, extension=".png"):
        return "%s-%sx%s@%sx%s" % (imagename, self.size,
                                   self.size, self.scale, extension)


class Blueprint(object):
    def __init__(self, definitions):
        self.definitions = definitions

    @classmethod
    def make_drawables(cls):
        definitions = [
            ImageDefinition(Idiom.UNIVERSAL, 1),
            ImageDefinition(Idiom.UNIVERSAL, 1.5),
            ImageDefinition(Idiom.UNIVERSAL, 2),
            ImageDefinition(Idiom.UNIVERSAL, 3)
        ]

        return cls(definitions)

    @classmethod
    def make_imageset_blueprint(cls):
        definitions = [
            ImageDefinition(Idiom.UNIVERSAL, 1),
            ImageDefinition(Idiom.UNIVERSAL, 2),
            ImageDefinition(Idiom.UNIVERSAL, 3)
        ]

        return cls(definitions)

    @classmethod
    def make_appiconset_blueprint(cls):
        definitions = [
            ImageDefinition(Idiom.IPHONE, 2, "20"),
            ImageDefinition(Idiom.IPHONE, 3, "20"),
            ImageDefinition(Idiom.IPHONE, 1, "29"),
            ImageDefinition(Idiom.IPHONE, 2, "29"),
            ImageDefinition(Idiom.IPHONE, 3, "29"),
            ImageDefinition(Idiom.IPHONE, 2, "40"),
            ImageDefinition(Idiom.IPHONE, 3, "40"),
            ImageDefinition(Idiom.IPHONE, 1, "57"),
            ImageDefinition(Idiom.IPHONE, 2, "57"),
            ImageDefinition(Idiom.IPHONE, 2, "60"),
            ImageDefinition(Idiom.IPHONE, 3, "60"),
            ImageDefinition(Idiom.IPAD, 1, "20"),
            ImageDefinition(Idiom.IPAD, 2, "20"),
            ImageDefinition(Idiom.IPAD, 1, "29"),
            ImageDefinition(Idiom.IPAD, 2, "29"),
            ImageDefinition(Idiom.IPAD, 1, "40"),
            ImageDefinition(Idiom.IPAD, 2, "40"),
            ImageDefinition(Idiom.IPAD, 1, "50"),
            ImageDefinition(Idiom.IPAD, 2, "50"),
            ImageDefinition(Idiom.IPAD, 1, "72"),
            ImageDefinition(Idiom.IPAD, 2, "72"),
            ImageDefinition(Idiom.IPAD, 1, "76"),
            ImageDefinition(Idiom.IPAD, 2, "76"),
            ImageDefinition(Idiom.IPAD, 2, "83.5"),
            ImageDefinition(Idiom.MARKETING, 1, "1024")
        ]

        return cls(definitions)
