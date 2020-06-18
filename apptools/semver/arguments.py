import argparse

from apptools.config import config


class Version(object):
    def __init__(self, major: int, minor: int, patch: int) -> None:
        self.major = major
        self.minor = minor
        self.patch = patch

    @staticmethod
    def parse(raw: str) -> "Version": 
        major, minor, patch = raw.split(".")

        return Version(int(major), int(minor), int(patch))

    def __eq__(self, other: "Version"):
        if other.major != self.major:
            return False

        if other.minor > self.minor:
            return False

        if other.patch > self.patch and other.minor == self.minor:
            return False

        return True

    def __str__(self):
        return f"{self.major}.{self.minor}.{self.patch}"


def semver(raw: str):
    requested_version = Version.parse(raw)
    version = Version.parse(config.VERSION)

    if version != requested_version:
        raise argparse.ArgumentTypeError(
                f"Invalid app-tools version {version} required: {requested_version}. Either change branch run or `python3 -m pip install .` in the app.tools git directory."
        )


parser = argparse.ArgumentParser(allow_abbrev=False, add_help=False)
parser.add_argument("-r",
        "--requirement",
        help="Requested version",
        required=False,
        type=semver)

