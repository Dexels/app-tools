from argparse import ArgumentParser, ArgumentTypeError
from json import JSONDecodeError, loads

from apptools.image.core.spec import Spec


def spec(path):
    # Try to load in the file
    content = None
    try:
        with open(path, 'r') as fp:
            content = fp.read()
    except IOError as e:
        raise ArgumentTypeError(e.strerror)

    # Try to convert to json
    json = None
    try:
        json = loads(content)
    except JSONDecodeError as e:
        raise ArgumentTypeError(
            'JSONDecodeError: line: %s column: %s (char %s)' %
            (e.lineno, e.colno, e.pos))

    # Try to transform to Spec objects
    # spec = None
    try:
        spec = Spec.load_from_json(json)
    except KeyError as e:
        raise ArgumentTypeError(e)

    return spec


# A parser to load the spec.json file. This parser can be used by multiple tools as a parent.
spec_parser = ArgumentParser(add_help=False)
spec_parser.add_argument('-s',
                         '--spec',
                         required=True,
                         type=spec,
                         help='path to the spec json file')
