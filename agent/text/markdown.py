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
    node: Node  # the parent node (e.g. a section)
    offset: int  # number of bytes from node.start_byte to the slice end


def get_text(node: Node) -> str:
    return node.text.decode().strip()


def get_slice(node_slice: NodeSlice) -> str:
    text = get_text(node_slice.node)
    return text[: node_slice.offset]


def slice_before(parent: Node) -> NodeSlice:
    child = parent.children[0]
    offset = child.end_byte - parent.start_byte
    return NodeSlice(parent, offset)


def print_meta(node: Node):
    start, end = node.byte_range
    size = end - start
    text = get_text(node)
    print(
        cs.paint(node.type, cs.Code.RED),
        cs.paint(f"({start}, {end})", cs.Code.WHITE),
        cs.paint(f"{size}", cs.Code.CYAN),
        cs.paint(f"{text[:30]!r}", cs.Code.GREEN),
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

    query = ts.query("markdown", "(section) @sec")
    captures = ts.captures(query, tree.root_node)
    nodes = sorted(captures["sec"], key=lambda n: n.start_byte)

    # get a unique set of children (dedup nodes)
    children = list({n for n in nodes if n.start_byte > n.parent.start_byte})

    # get a unique set of parents and map them to their children
    parents = {}
    for c in children:
        v = parents.get(c.parent, [])
        if v:
            v.append(c)
        else:
            v = [c]
        parents[c.parent] = sorted(v, key=lambda n: n.start_byte)

    print(
        f"captures: ({len(captures)}), "
        f"parents ({len(parents)}), "
        f"children ({len(children)}), "
    )

    # Note: Large blobs are usually ~5k or greater
    for p, c in parents.items():
        print(cs.paint("---parent---", cs.Code.MAGENTA))
        print_meta(p)
        print_text(p, args.margin)
        print(cs.paint("---children---", cs.Code.MAGENTA))
        for n in c:
            print_meta(n)
            print_text(n, args.margin)
