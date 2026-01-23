# agent/text/markdown.py
"""
Honestly, it needs a bit of tweaking, but I think I can make this work.
"""

import functools
from typing import Iterable

from tree_sitter import Node, Tree

from agent.text.sitter import TextSitter


# A couple of tree-sitter related edge cases I ran into were
# Markdown and HTML which only have 1 or 2 nodes. This requires
# recursion for text extraction.
# This class is a light-weight abstraction for managing dependency injection.
# The goal of this class is to keep usage readable and consistent.
class Markdown:
    @staticmethod
    def is_named(node: Node) -> bool:
        return node.is_named

    @staticmethod
    def is_document(node: Node) -> bool:
        # the root node contains the entire documents text.
        # this creates a giant blob of duplicated text.
        # we just want to get the chunks from the child objects.
        return node.type == "document" or node.parent.type == "document"

    @staticmethod
    def is_section(node: Node) -> bool:
        return node.type == "section"

    @staticmethod
    def text(node: Node) -> str:
        return node.text.decode("utf-8")

    @staticmethod
    def tree(path_or_data: str | bytes) -> Tree:
        # Parse source or a file into a tree_sitter.Tree.
        path = Path(path_or_data)
        if path.is_file():
            path_or_data = path.read_bytes()
        return TextSitter.tree("markdown", path_or_data)

    @staticmethod
    def walk(root: Node) -> Iterable[Node]:
        # Depth-first traversal that yields each node exactly once.
        return TextSitter.walk(root)


if __name__ == "__main__":
    from argparse import ArgumentParser, Namespace
    from pathlib import Path
    from types import CapsuleType
    from typing import Iterable

    def parse_args() -> Namespace:
        parser = ArgumentParser()
        parser.add_argument("path", help="Path to the source file.")
        return parser.parse_args()

    args = parse_args()

    # note: sometimes sections will overlap, leading to duplicate entries.
    seen = set()
    tree = Markdown.tree(args.path)
    root = tree.root_node
    print(f"Root has {root.child_count} child(ren)")

    for node in Markdown.walk(root):
        if not Markdown.is_named(node):
            continue
        if not Markdown.is_section(node):
            continue
        if Markdown.is_document(node):
            continue

        # todo: leverage the range (start and end) to find overlapping regions.
        start, end = node.byte_range
        text = Markdown.text(node)
        seen.add(text)

        # print("@@@")
        # print(f"{node.type:>10} | offset {start}-{end} | {end - start} bytes")
        # print("@@@")
        # print(text)

    # some chunks are too big while others are too small.
    # the small chunks are usually components of larger chunks.
    # the smaller chunk will not match the content within the larger
    # chunk, still leading to duplicate entries.
    for i, text in enumerate(seen):
        print(f"[{i}]: {text}")
