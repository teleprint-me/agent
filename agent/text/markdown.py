# agent/text/markdown.py
import functools
from typing import Iterable

from tree_sitter import Node, Tree

from agent.text.sitter import TextSitter


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
        path = Path(path_or_data)
        if path.is_file():
            path_or_data = path.read_bytes()
        return TextSitter.tree("markdown", path_or_data)

    @staticmethod
    def walk(root: Node) -> Iterable[str]:
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
    root = Markdown.tree(args.path)
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

        print("@@@")
        print(f"{node.type:>10} | offset {start}-{end} | {end - start} bytes")
        print("@@@")
        print(text)
