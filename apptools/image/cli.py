#!/usr/bin/env python3

from argparse import ArgumentParser
from sys import exit

from apptools.image.core.parser import spec_parser
from apptools.image.image.distribute import distribute


def main():
    parser = ArgumentParser(allow_abbrev=False, parents=[spec_parser])
    parser.add_argument('-t',
                        '--target',
                        help='only build for a specific target')
    parser.add_argument('-o',
                        '--overwrite',
                        help='Overwrite a specific spec settings',
                        required=False,
                        action='append')

    args = parser.parse_args()

    distribute(args.spec, args.target, args.overwrite)

    exit()


if __name__ == "__main__":
    main()
