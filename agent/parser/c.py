#!/usr/bin/env python3
"""
A tiny, standalone C parser that splits a file into “chunks”:
  - consecutive #include directives
  - function definitions
  - struct/enum definitions
  - everything else (globals, macros, etc.)
"""

import sys
from pathlib import Path

import tree_sitter_c as tsc # pip: tree-sitter-c
from tree_sitter import Language, Parser, Node

def read_bytes(path: str) -> bytes:
    return Path(path).read_bytes()


# returns a capsule instance
capsule = tsc.language()
# must pass capsule to get language instance
lang = Language(capsule)
# parser accepts the language instance object
parser = Parser(lang)
print(lang)
print(parser)

