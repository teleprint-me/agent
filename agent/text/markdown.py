# agent/text/markdown.py
"""
Markdown parsing helper built on top of :mod:`tree_sitter`.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Tuple

from tree_sitter import Node, Tree

from agent.text import color
from agent.text.sitter import TextSitter as ts


def get_text(node: Node) -> str:
    return node.text.decode().strip()


def print_meta(node: Node):
    start, end = node.byte_range
    size = end - start
    text = get_text(node)
    print(
        color.paint(node.type, color.Code.RED),
        color.paint(f"({start}, {end})", color.Code.WHITE),
        color.paint(f"{size}", color.Code.GREEN),
        color.paint(f"{text[:30].split()}", color.Code.BLUE),
    )


def print_text(node: Node, margin: int = 30):
    start, end = node.byte_range
    text = node.text.decode().strip()
    print(color.paint(f"start-of-text({start})", fg=color.Code.YELLOW))
    if margin > 0:
        print(text[:margin])
    else:
        print(text)
    print(color.paint(f"end-of-text({end})", fg=color.Code.YELLOW))


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
    blocks = captures["block"]
    blocks = sorted(blocks, key=lambda b: b.start_byte)

    print(f"Captures: keys ({len(captures)}), blocks ({len(blocks)})")
    for blk in blocks:
        print_meta(blk)
        print_text(blk, margin=args.margin)
