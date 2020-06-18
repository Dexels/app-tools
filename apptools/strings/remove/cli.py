#!/usr/bin/env python3

import argparse
import json
import pathlib
import re
import sys

description = "Remove a key from translations file"


def main():
    parser = argparse.ArgumentParser(add_help=False, description=description)
    parser.add_argument("-i", "--input", help="Strings directory",
                        required=True, type=pathlib.Path)
    parser.add_argument("-k", "--key", help="Key", required=True)

    args = parser.parse_args()

    exec(args.input, args.key)

    sys.exit(0)


def exec(path: pathlib.Path, key: str) -> None:
    pattern = re.compile(f'"key"\s*:\s*"{key}"')

    for path in path.rglob("*.json"):
        lines = []

        with open(path, "r+") as fp:
            for line in fp:
                if pattern.search(line) is None:
                    lines.append(line)

            fp.seek(0)
            fp.truncate()
            fp.write("".join(lines))


if __name__ == "__main__":
    main()
