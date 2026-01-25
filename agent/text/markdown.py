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


def get_text(node: Node) -> str:
    return node.text.decode().strip()


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
    query = ts.query("markdown", """(section) @block""")
    captures = ts.captures(query, tree.root_node)

    # extract the captured nodes
    blocks = sorted(captures["block"], key=lambda b: b.start_byte)

    # filter out parent nodes
    sections = [b for b in blocks if b.start_byte > b.parent.start_byte]

    print(
        f"Captures: keys ({len(captures)}), "
        f"blocks ({len(blocks)}), "
        f"sections ({len(sections)})"
    )

    # This works for the most part, but I need slices from the parent nodes
    # e.g. if parent is 0, 320 and child is 116, 171, then get a slice of the
    # parent from 0 - 116. There doesn't seem to be sane way to get a node out
    # this process and the nodes are required to retain related metadata.
    for sec in sections:
        print_meta(sec)
        print_text(sec, margin=args.margin)
