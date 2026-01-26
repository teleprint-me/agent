# agent/text/markdown.py
"""
Markdown parsing helper built on top of :mod:`tree_sitter`.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Tuple

from tree_sitter import Node, Tree

from agent.text import color as cs
from agent.text.sitter import TextSitter as ts


@dataclass(frozen=True)
class NodeSlice:
    start: int  # the start offset
    end: int  # the end offset
    parent: Node
    child: Node
    text: str  # the slice of text


def get_text(node: Node) -> str:
    return node.text.decode().strip()


def node_size(node: Node) -> int:
    return node.end_byte - node.start_byte


def print_node(node: Node, margin: int = 30):
    size = node_size(node)
    text = get_text(node)
    print(
        cs.paint(f"({node.type})", cs.Code.YELLOW),
        cs.paint(f"{node.byte_range}", cs.Code.WHITE),
        cs.paint(f"{size} bytes", cs.Code.RED),
        cs.paint(f"{text[:margin]!r}", cs.Code.GREEN),
    )


if __name__ == "__main__":  # pragma: no cover - manual testing only
    import argparse

    parser = argparse.ArgumentParser(description="Parse markdown and print sections")
    parser.add_argument("path", help="Path to a markdown file.")
    parser.add_argument(
        "-m",
        "--margin",
        type=int,
        default=30,
        help="Number of bytes to print to stdout (default: 30).",
    )
    args = parser.parse_args()

    tree = ts.tree("markdown", Path(args.path).read_text())

    seen = set()
    sections = set()
    for node in ts.walk(tree.root_node):
        if not node.is_named:
            continue
        if node in seen:
            continue

        size = node_size(node)
        if not size > 0:
            continue  # empty node

        if (
            node.type != "section"
            and node.parent
            and node.parent.type not in ["document", "section"]
        ):
            continue  # probably list, inline, paragraph, etc.

        print_node(node, args.margin)

        seen.add(node)
