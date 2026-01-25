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


@dataclass
class NodeSlice:
    parent: Node  # the parent node (e.g. a section)
    offset: int  # the part that belongs only to this node


def get_text(node: Node) -> str:
    return node.text.decode().strip()


def get_slice(node_slice: NodeSlice) -> str:
    text = get_text(node_slice.parent)
    return text[: node_slice.offset]


def slice_before(parent: Node) -> NodeSlice:
    child = parent.children[0]
    offset = child.start_byte - parent.start_byte
    return NodeSlice(parent, offset)


def slice_nodes(tree: Tree) -> NodeSlice:
    query = ts.query("markdown", "(section) @sec")
    captures = ts.captures(query, tree.root_node)
    sections = [c for c in captures["sec"] if c.start_byte > c.parent.start_byte]
    slices = [slice_before(s.parent) for s in sections]
    print(
        f"Captures: keys ({len(captures)}), "
        f"sections ({len(sections)}), "
        f"slices ({len(slices)})"
    )
    return slices


def print_meta(node: Node):
    start, end = node.byte_range
    size = end - start
    text = get_text(node)
    print(
        cs.paint(node.type, cs.Code.RED),
        cs.paint(f"({start}, {end})", cs.Code.WHITE),
        cs.paint(f"{size}", cs.Code.GREEN),
        cs.paint(f"{text[:30].split()}", cs.Code.BLUE),
    )


def print_text(node: Node, margin: int = 30):
    start, end = node.byte_range
    text = get_text(node)
    print(cs.paint(f"start-of-text({start})", fg=cs.Code.YELLOW))
    if margin > 0:
        print(text[:margin])
    else:
        print(text)
    print(cs.paint(f"end-of-text({end})", fg=cs.Code.YELLOW))


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
    slices = slice_nodes(tree)

    # This works for the most part, but I need slices from the parent nodes
    # e.g. if parent is 0, 320 and child is 116, 171, then get a slice of the
    # parent from 0 - 116. There doesn't seem to be sane way to get a node out
    # this process and the nodes are required to retain related metadata.
    for s in slices:
        print_meta(s.parent)
        text = get_slice(s)
        print(cs.paint(text, fg=cs.Code.YELLOW))
