#!/usr/bin/env python3
"""
https://tree-sitter.github.io/py-tree-sitter/

A tiny, standalone C parser that splits a file into "chunks":
  - consecutive #include directives
  - function definitions
  - struct/enum definitions
  - everything else (globals, macros, etc.)
"""

import sys
from argparse import ArgumentParser, Namespace
from pathlib import Path

import magic
import tree_sitter_c as tsc  # pip: tree-sitter-c
from tree_sitter import Language, Node, Parser


def read_bytes(path: str) -> bytes:
    return Path(path).read_bytes()


def parse_args() -> Namespace:
    parser = ArgumentParser()
    parser.add_argument("path", type=str, help="The python source file to parse.")
    return parser.parse_args()


args = parse_args()

# only parse the file if it's a C source
file_magic = magic.detect_from_filename(args.path)
if file_magic.encoding != "utf-8":
    raise RuntimeError("File is not UTF‑8")
if file_magic.mime_type != "text/x-c":
    raise RuntimeError("File is not a C source")
if "C source" not in file_magic.name:
    raise RuntimeError("File is not a C source")

capsule = tsc.language()
lang = Language(capsule)
parser = Parser(lang)
source = read_bytes(args.path)
tree = parser.parse(source)

for node in tree.root_node.children:
    if node.type == ";":
        continue
    print(f"type: {node.type}, start: {node.start_byte}, end: {node.end_byte}")
    print("---")
    txt = node.text.decode()
    nxt = node.next_sibling
    if nxt and nxt.type == ";":
        txt += nxt.text.decode()
    print(txt)
    print("---")
