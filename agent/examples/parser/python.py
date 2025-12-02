import ast
from argparse import ArgumentParser, Namespace
from typing import List

parser = ArgumentParser()
parser.add_argument("file", type=str, help="The python source file to parse.")
args = parser.parse_args()

source = ""
with open(args.file) as file:
    source = file.read()

lines = source.splitlines(keepends=True)
for line in lines:
    print(line, end="")
