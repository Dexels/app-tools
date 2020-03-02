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


class Size(object):
    def __init__(self, width, height):
        self.width = width
        self.height = height

    @classmethod
    def square(cls, length):
        return Size(length, length)


class ImageDefinition(object):
    def __init__(self, idiom, scale, size=None):
        self.idiom = idiom
        self.scale = scale
        self.size = size

    def filename(self, imagename, extension=".png"):
        return "%s-%sx%s@%sx%s" % (imagename, self.size.width,
                                   self.size.height, self.scale, extension)


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
            ImageDefinition(Idiom.IPHONE, 2, Size.square(20)),
            ImageDefinition(Idiom.IPHONE, 3, Size.square(20)),
            ImageDefinition(Idiom.IPHONE, 1, Size.square(29)),
            ImageDefinition(Idiom.IPHONE, 2, Size.square(29)),
            ImageDefinition(Idiom.IPHONE, 3, Size.square(29)),
            ImageDefinition(Idiom.IPHONE, 2, Size.square(40)),
            ImageDefinition(Idiom.IPHONE, 3, Size.square(40)),
            ImageDefinition(Idiom.IPHONE, 1, Size.square(57)),
            ImageDefinition(Idiom.IPHONE, 2, Size.square(57)),
            ImageDefinition(Idiom.IPHONE, 2, Size.square(60)),
            ImageDefinition(Idiom.IPHONE, 3, Size.square(60)),
            ImageDefinition(Idiom.IPAD, 1, Size.square(20)),
            ImageDefinition(Idiom.IPAD, 2, Size.square(20)),
            ImageDefinition(Idiom.IPAD, 1, Size.square(29)),
            ImageDefinition(Idiom.IPAD, 2, Size.square(29)),
            ImageDefinition(Idiom.IPAD, 1, Size.square(40)),
            ImageDefinition(Idiom.IPAD, 2, Size.square(40)),
            ImageDefinition(Idiom.IPAD, 1, Size.square(50)),
            ImageDefinition(Idiom.IPAD, 2, Size.square(50)),
            ImageDefinition(Idiom.IPAD, 1, Size.square(72)),
            ImageDefinition(Idiom.IPAD, 2, Size.square(72)),
            ImageDefinition(Idiom.IPAD, 1, Size.square(76)),
            ImageDefinition(Idiom.IPAD, 2, Size.square(76)),
            ImageDefinition(Idiom.IPAD, 2, Size.square(83.5)),
            ImageDefinition(Idiom.MARKETING, 1, Size.square(1024))
        ]

        return cls(definitions)
