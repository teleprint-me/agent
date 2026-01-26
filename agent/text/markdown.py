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
    captures = ts.captures(query, tree.root_node)

    seen = set()
    slices = list()
    for node in captures["sec"]:
        if node in seen:
            continue

        # only capture children that are sections
        # if we don't do this, children will almost always be true.
        # we can filter nodes we don't care about by doing this.
        sections = ts.captures(query, node)["sec"]
        print(sections)

        # check if the current node is an only-child
        if 1 == len(sections):  # not a parent
            print("discovered child")
            # get the entire body of text since there are no subsections
            node_slice = NodeSlice(
                node.start_byte,
                node.end_byte,
                get_size(node),
                node,
                get_text(node),
            )
            # add the child slice to sections
            slices.append(node_slice)
            seen.add(node)
            continue

        # check if the current node has a parent
        if len(sections) > 1:
            print("discovered parent")
            # do not duplicate the root nodes
            for sec in sections:
                if sec in seen:
                    continue
                if sec.parent.type == "document":
                    continue
                # get the difference between the parent and the current node
                # start from beginning of parent and end at beginning of child
                start_byte = sec.parent.start_byte
                end_byte = sec.start_byte
                size = get_size(sec)
                # slice out the unique text from the parent (get a unique slice)
                parent_text = get_text(sec.parent)[start_byte:end_byte].strip()
                if not parent_text:  # empty slice
                    continue  # nothing to extract
                node_slice = NodeSlice(
                    start_byte, end_byte, size, sec.parent, parent_text
                )
                # add the parent slice to sections
                slices.append(node_slice)
                seen.add(sec)

    for s in slices:
        print_slice(s, args.margin)
        print(s.text)
