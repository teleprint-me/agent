"""
https://docs.python.org/3/library/ast.html
"""

import ast
import re
from argparse import ArgumentParser, Namespace
from typing import List
import magic


def open_file(path: str) -> str:
    """return the raw source file as a string."""
    source = ""
    with open(path) as file:
        source = file.read()
    return source


def start_line(node: ast.AST) -> int:
    start = node.lineno - 1  # start is inclusive
    if hasattr(node, "decorator_list"):
        for decorator in node.decorator_list:
            start = min(start, decorator.lineno - 1)
    return start


def end_line(node: ast.AST) -> int:
    return node.end_lineno  # end is exclusive


def slice_block(lines: List[str], start: int, end: int) -> str:
    return "".join(lines[start:end])


def parse_args() -> Namespace:
    parser = ArgumentParser()
    parser.add_argument("path", type=str, help="The python source file to parse.")
    return parser.parse_args()


args = parse_args()

# assert the source file is a python script or module
file_magic = magic.detect_from_filename(args.path)
assert "utf-8" == file_magic.encoding, "File is not UTF-8 encoded"
assert "text/plain" == file_magic.mime_type, "File is not text/plain"
assert "Python script" in file_magic.name, "File is not a Python script"

source = open_file(args.path)
lines = source.splitlines(keepends=True)
tree = ast.parse(source)
chunks = []
used = set()  # chunked lines
# import state machine
import_start = None
import_end = None

for node in tree.body:
    start: int = start_line(node)
    end: int = end_line(node)

    # consecutive import block (group all inclusions)
    if isinstance(node, (ast.Import, ast.ImportFrom)):
        if import_start is None:
            import_start = start
        import_end = end
        continue

    # flush pending import block
    if import_start is not None:
        chunks.append(slice_block(lines, import_start, import_end))
        import_start = import_end = None

    if isinstance(node, ast.ClassDef):
        # need to handle decorators
        methods = []
        for child in node.body:
            if isinstance(child, ast.FunctionDef):
                mstart = start_line(child)
                mend = end_line(child)
                methods.append((mstart, mend))

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
        # everything else (defs, ifs, etc.)
        if start not in used:
            chunks.append(slice_block(lines, start, end))
            used.update(range(start, end))

print("Aggregated Chunks:")
for i, chunk in enumerate(chunks):
    print(f"Chunk {i}\n---")
    print(chunk, end="")
    print("---")
