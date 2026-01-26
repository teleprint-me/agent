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
    start: int  # start offset
    end: int  # end offset
    size: int  # diff between end and start
    node: Node  # node text was extracted from
    text: str  # extracted content


def get_text(node: Node) -> str:
    return node.text.decode("utf-8").strip()


def get_size(node: Node) -> int:
    return node.end_byte - node.start_byte


def print_node(node: Node, margin: int = 30):
    size = get_size(node)
    text = get_text(node)
    print(
        cs.paint(f"({node.type})", cs.Code.YELLOW),
        cs.paint(f"{node.byte_range}", cs.Code.WHITE),
        cs.paint(f"{size} bytes", cs.Code.RED),
        cs.paint(f"{text[:margin]!r}", cs.Code.GREEN),
    )


def print_slice(slice: NodeSlice, margin: int = 30):
    print(
        cs.paint(f"({slice.node.type})", cs.Code.YELLOW),
        cs.paint(f"({slice.start}, {slice.end})", cs.Code.WHITE),
        cs.paint(f"{slice.size} bytes", cs.Code.RED),
        cs.paint(f"{slice.text[:margin]!r}", cs.Code.GREEN),
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

    source_bytes = Path(args.path).read_bytes()
    tree = ts.tree("markdown", source_bytes)

    # capture all nodes of type "section".
    # note: we can reuse the query as many times as needed.
    query = ts.query("markdown", "(section) @sec")
    # captures is an unordered mapping
    captures = ts.captures(query, tree.root_node)
    # sort the captures
    captures["sec"] = sorted(captures["sec"], key=lambda s: s.start_byte)

    seen = set()
    slices = list()
    for cap in captures["sec"]:
        print("capture", end="=")
        print_node(cap)

        # only capture children that are sections
        # if we don't do this, node.children will always be true.
        # we can filter nodes we don't care about by doing this.
        sections = sorted(ts.captures(query, cap)["sec"], key=lambda s: s.start_byte)
        # check if the current node is a leaf node
        if 1 == len(sections):  # not a parent
            leaf = sections[0]
            if leaf in seen:
                continue

            print("leaf", end="=")
            print_node(leaf)

            # get the entire body of text since there are no subsections
            node_slice = NodeSlice(
                leaf.start_byte,
                leaf.end_byte,
                get_size(leaf),
                leaf,
                get_text(leaf),
            )
            # add the child slice to sections
            slices.append(node_slice)
            seen.add(leaf)
            continue

        # check if the current node has a parent
        if len(sections) > 1:
            print("relatives")
            # do not duplicate the root nodes
            for child in reversed(sections):
                print_node(child)
                if child in seen:
                    print("seen")
                    continue
                if child.parent.type == "document":
                    print("root", end="=")
                    print_node(child)
                    break  # found root node
                # get the difference between the parent and child nodes
                # start from beginning of parent and end at beginning of child
                start_byte = child.parent.start_byte
                end_byte = child.start_byte
                # slice out the unique text from the parent (get a unique slice)
                parent_slice = child.parent.text[start_byte:end_byte].decode().strip()
                if not parent_slice:  # empty slice
                    continue  # nothing to extract
                node_slice = NodeSlice(
                    start_byte,
                    end_byte,
                    get_size(child),
                    child.parent,
                    parent_slice,
                )
                # add the parent slice to sections
                slices.append(node_slice)
                seen.add(child)

    print(cs.paint("--- slices ---", cs.Code.MAGENTA))
    for s in slices:
        print_slice(s, args.margin)
        print(s.text)
