#!/usr/bin/env python3

import argparse
import sys

from typing import Mapping, Callable, List

from apptools.entity.arguments import parser as parent_parser

from apptools.entity.writer import write
from apptools.entity.java.writer import write as java_write
from apptools.entity.swift.writer import write as swift_write
from apptools.entity.typescript.writer import write as typescript_write

description = "Transform entities to models in n programming languages"


def main():
    parser = argparse.ArgumentParser(allow_abbrev=False,
                                     description=description)
    subparsers = parser.add_subparsers(help="Supported writers")

    java_parser = subparsers.add_parser(name="java", parents=[parent_parser])
    java_parser.set_defaults(writer=java_write)

    swift_parser = subparsers.add_parser(name="swift", parents=[parent_parser])
    swift_parser.set_defaults(writer=swift_write)

    typescript_parser = subparsers.add_parser(name="typescript",
                                              parents=[parent_parser])
    typescript_parser.set_defaults(writer=typescript_write)

    args = parser.parse_args()

    # Call writer.
    sys.exit(write(args.writer, vars(args)))

if __name__ == "__main__":
    main()
