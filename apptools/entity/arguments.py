import argparse
import pathlib

parser = argparse.ArgumentParser(add_help=False)
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
