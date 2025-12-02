"""
https://docs.python.org/3/library/ast.html
"""

import ast
import re
from argparse import ArgumentParser, Namespace
from typing import List


def open_file(path: str) -> str:
    """return the raw source file as a string."""
    source = ""
    with open(path) as file:
        source = file.read()
    return source


def start_line(node: ast.AST) -> int:
    return node.lineno - 1


def end_line(lines: List[str], start: int) -> int:
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
    return end


def slice_block(lines: List[str], start: int, end: int) -> str:
    return "".join(lines[start:end])


def parse_args() -> Namespace:
    parser = ArgumentParser()
    parser.add_argument("path", type=str, help="The python source file to parse.")
    return parser.parse_args()


args = parse_args()
source = open_file(args.path)
lines = source.splitlines(keepends=True)
tree = ast.parse(source)
chunks = []
used = set() # chunked lines

for node in tree.body:
    start: int = start_line(node)
    end: int = end_line(lines, start)

    # start is inclusive, end is exclusive
    print(f"start: {start + 1}, end: {end}, {node}")

    if isinstance(node, ast.FunctionDef):
        # top-level function
        chunks.append(slice_block(lines, start, end))
        used.update(range(start, end))
        print(chunks)
        print(used)

