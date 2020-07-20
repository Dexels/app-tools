import argparse
import pathlib

from apptools.semver.arguments import parser as semver_parser

parser = argparse.ArgumentParser(add_help=False, parents=[semver_parser])
parser.add_argument("-u",
                    "--username",
                    help="username for the navajo user",
                    required=True)
parser.add_argument("-p",
                    "--password",
                    help="password for the navajo user",
                    required=True)
parser.add_argument("-i",
                    "--input",
                    help="Entity directory",
                    required=True,
                    type=pathlib.Path)
parser.add_argument("-o",
                    "--output",
                    help="Output directory",
                    required=True,
                    type=pathlib.Path)
parser.add_argument("-s",
                    "--skip",
                    help="Skip these entities",
                    required=False,
                    action='append')
parser.add_argument("-e",
                    "--entities",
                    help="Only these entities",
                    required=False,
                    action='append')
