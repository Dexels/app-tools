#!/usr/bin/env python3

import argparse
import pathlib
import sys

from typing import Mapping, Callable, List

from apptools.strings.arguments import parser as parent_parser
from apptools.strings.writer import write
from apptools.strings.java.writer import write as java_write
from apptools.strings.swift.writer import write as swift_write

description = "Translation"


def main():
    parser = argparse.ArgumentParser(allow_abbrev=False,
                                     description=description)
    subparsers = parser.add_subparsers(help="Supported writers")

    java_parser = subparsers.add_parser(name="java", parents=[parent_parser])
    java_parser.set_defaults(writer=java_write)

    swift_parser = subparsers.add_parser(name="swift", parents=[parent_parser])
    swift_parser.set_defaults(writer=swift_write)

    args = parser.parse_args()

    sys.exit(write(args.writer, vars(args)))


if __name__ == "__main__":
    main()
