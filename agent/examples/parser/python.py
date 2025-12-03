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
    return node.lineno - 1 # start is inclusive


def end_line(node: ast.AST) -> int:
    return node.end_lineno  # end is exclusive


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
used = set()  # chunked lines

for node in tree.body:
    start: int = start_line(node)
    end: int = end_line(node)

    print(f"parent: {node}")
    print(f"start: {start + 1}, end: {end}")
    print(vars(node), end="\n\n")

    if isinstance(node, ast.FunctionDef):
        # top-level function
        chunks.append(slice_block(lines, start, end))
        used.update(range(start, end))
    elif isinstance(node, ast.ClassDef):
        # need to handle decorators
        methods = []
        for child in node.body:
            print(f"child: {child}")
            print(vars(node))
            if isinstance(child, ast.FunctionDef):
                mstart = start_line(child)
                mend = end_line(child)
                methods.append((mstart, mend))
            print()

        cursor = start
        cls_chunks = []
        for mstart, mend in sorted(methods):
            if cursor < mstart:
                cls_chunks.append(slice_block(lines, cursor, mstart))
                used.update(range(cursor, mstart))
            cursor = mend

        if cursor < end:
            cls_chunks.append(slice_block(lines, cursor, end))
            used.update(range(cursor, end))

        for chunk in cls_chunks:
            if chunk.strip():
                chunks.append(chunk)

        for mstart, mend in methods:
            chunks.append(slice_block(lines, mstart, mend))
            used.update(range(mstart, mend))
    else:
        if start not in used:
            chunks.append(slice_block(lines, start, end))
            used.update(range(start, end))

print("Aggregated Chunks:")
for i, chunk in enumerate(chunks):
    print(f"Chunk {i}\n---")
    print(chunk, end="")
    print("---")
