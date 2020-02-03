import argparse
import pathlib

parser = argparse.ArgumentParser(add_help=False)
parser.add_argument("-d",
                    "--default",
                    help="Default language",
                    required=True,
                    type=str)
parser.add_argument("-l",
                    "--language",
                    help="Language",
                    required=False,
                    type=str)
parser.add_argument("-t",
                    "--target",
                    help="App target",
                    required=False,
                    type=str)
parser.add_argument("-i",
                    "--input",
                    help="Strings directory",
                    required=True,
                    type=pathlib.Path)
parser.add_argument("-o",
                    "--output",
                    help="Output file",
                    required=True,
                    type=pathlib.Path)
parser.add_argument("-p",
                    "--platform",
                    help="Platform",
                    required=False,
                    type=str)
