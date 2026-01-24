# agent/text/markdown.py
"""
Markdown parsing helper built on top of :mod:`tree_sitter`.
"""

from __future__ import annotations

from pathlib import Path
from typing import Iterable, Tuple

from tree_sitter import Node, Tree

from agent.text.sitter import TextSitter

ESCAPE = "\x1b"
RESET = f"{ESCAPE}[0m"


def fg_256(n: int) -> str:
    """Return a foreground escape sequence for the given 0-255 code."""
    return f"{ESCAPE}[38;5;{n}m"


FG_PINK = fg_256(198)
FG_GREEN = fg_256(46)
FG_BLUE = fg_256(32)
FG_YELLOW = fg_256(226)
FG_GOLD = fg_256(214)


def hl_key(color: int, n: object) -> str:
    return f"{color}[{n}]{RESET}"


def hl_value(color: int, n: object) -> str:
    return f"{color}{n}{RESET}"


def print_meta(node: Node):
    start, end = node.byte_range
    size = end - start
    print(hl_value(FG_GREEN, node.type), (start, end), hl_value(FG_BLUE, size))


def print_text(node: Node):
    start, end = node.byte_range
    text = node.text.decode().strip()
    print(hl_key(FG_PINK, f"start-of-text({start})"), f"\n{text}")
    print(hl_key(FG_PINK, f"end-of-text({end})"))


if __name__ == "__main__":  # pragma: no cover - manual testing only
    import argparse

    parser = argparse.ArgumentParser(description="Parse markdown and print sections")
    parser.add_argument("path", help="Path to a markdown file.")
    args = parser.parse_args()

    tree = TextSitter.tree(lang_or_path=args.path, source=None)
    seen = []

    # Gather all (start,end,node) tuples for section nodes.
    for node in TextSitter.walk(tree.root_node):
        if not node.is_named:
            continue  # skip punctuation
        print_meta(node)
        if node.type == "section":
            start, end = node.byte_range
            seen.append((start, end, node))
    # Sort by starting byte offset.
    seen.sort(key=lambda t: t[0])

    print(hl_value(FG_YELLOW, "@@@seen@@@"))

    last_end = -1
    chunks = []
    for start, end, node in seen:
        if not node.is_named:
            continue
        start, end = node.byte_range
        size = end - start
        print_meta(node)
        if node.type == "document" or node.parent.type == "document":
            continue
        if (node.type == "section" and node.parent.type == "section") or (
            node.type == "section"
            and not any(child.type == "section" for child in node.children)
        ):
            print_text(node)
            chunks.append(node)
