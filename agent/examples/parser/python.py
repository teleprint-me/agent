"""
https://docs.python.org/3/library/ast.html
"""

import ast
from argparse import ArgumentParser, Namespace
from typing import List
import re

parser = ArgumentParser()
parser.add_argument("file", type=str, help="The python source file to parse.")
args = parser.parse_args()

source = ""
with open(args.file) as file:
    source = file.read()

lines = source.splitlines(keepends=True)
tree = ast.parse(source)
print(tree)
for node in tree.body:
    start = node.lineno - 1

    # compute final line
    first_indent = len(lines[start]) - len(lines[start].lstrip())
    end = start + 1
    n = len(lines)
    while end < n:
        line = lines[end]
        # empty/comment lines allowed
        if not line.strip():
            end += 1
            continue

        indent = len(line) - len(line.lstrip())
        if indent <= first_indent:
            break

        end += 1

    # start is inclusive, end is exclusive
    print(f"start: {start + 1}, end: {end}, {node}")
