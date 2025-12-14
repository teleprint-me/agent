# agent/parser/c.py
"""
https://tree-sitter.github.io/py-tree-sitter/

A tiny, standalone language parser that splits a source file into semantic "chunks":
  - consecutive import/include directives
  - function definitions
  - struct/enum definitions
  - everything else (globals, macros, etc.)
"""

import sys
from argparse import ArgumentParser, Namespace
from pathlib import Path

from agent.parser import loader

parser = ArgumentParser()
parser.add_argument("path", help="Path to a supported source file.")
args = parser.parse_args()

# store chunks
chunks = []
# note: need to group include, import, etc.

tree = loader.get_tree(args.path)
for node in tree.root_node.children:
    if node.type == ";":
        continue
    print(f"type: {node.type}, start: {node.start_byte}, end: {node.end_byte}")
    print("---")
    txt = node.text.decode()
    nxt = node.next_sibling
    if nxt and nxt.type == ";":
        txt += nxt.text.decode()

    # note: the python ast can break this down, but tree-sitter can not.
    # the advantage to tree-sitter admist this caveat is we can parse any supported lang.
    # if node.type == "class_definition":
    #     for child in node.children:
    #         print(child.text.decode())
    #         print("---")

    print(txt)
    print("---")
