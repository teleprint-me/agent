# agent/text/markdown.py
"""
Markdown parsing helper built on top of :mod:`tree_sitter`.
"""

from __future__ import annotations

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
    print(
        color.paint(f"start-of-text({start})", fg=color.Code.YELLOW),
        f"\n{text[:margin]}",
    )
    print(color.paint(f"end-of-text({end})", fg=color.Code.YELLOW))


if __name__ == "__main__":  # pragma: no cover - manual testing only
    import argparse

    parser = argparse.ArgumentParser(description="Parse markdown and print sections")
    parser.add_argument("path", help="Path to a markdown file.")
    args = parser.parse_args()

    tree = ts.tree(lang_or_path=args.path, source=None)
    query = ts.query("markdown", """[ (section) ]""")

    # last_child = cursor.goto
    seen = []

    # Gather all (start,end,node) tuples for section nodes.
    for node in ts.walk(tree.root_node):
        if node.type == "block_continuation":
            continue  # skip these
        if node.is_named:
            print_meta(node)
            print_text(node)
