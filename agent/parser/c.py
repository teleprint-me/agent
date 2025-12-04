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

# assert the source file is a python script or module
file_magic = magic.detect_from_filename(args.path)
assert "utf-8" == file_magic.encoding, "File is not UTF-8 encoded"
assert "text/x-c" == file_magic.mime_type, "File is not text/x-c"
assert "C source" in file_magic.name, "File is not a C source"

# returns a capsule instance
capsule = tsc.language()
# must pass capsule to get language instance
lang = Language(capsule)
# parser accepts the language instance object
parser = Parser(lang)
# get the source file as byte code
source = read_bytes(args.path)
# tree sitter expects raw byte code
tree = parser.parse(source)

print(tree)
for node in tree.root_node.children:
    print(node.type)
    print("---")
    print(source[node.start_byte:node.end_byte].decode(file_magic.encoding))
    print("---")

