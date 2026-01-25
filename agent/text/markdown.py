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
        default=300,
        help="Number of bytes to print to stdout (default: 30).",
    )
    args = parser.parse_args()

    tree = ts.tree("markdown", Path(args.path).read_text())
    root = tree.root_node

    query = ts.query("markdown", "(section) @sec")
    captures = ts.captures(query, tree.root_node)
    nodes = sorted(captures["sec"], key=lambda n: n.start_byte)

    # get a unique set of children (dedup nodes)
    children = list({n for n in nodes if n.start_byte > n.parent.start_byte})

    # get a unique set of parents and map them to their children
    parents = dict()
    for child in children:
        rent = parents.get(child.parent, set())
        rent.add(child)
        parents[child.parent] = set(sorted(rent, key=lambda n: n.start_byte))

    print(
        f"document: {root.end_byte} bytes, "
        f"captures: ({len(captures)}), "
        f"parents ({len(parents)}), "
        f"children ({len(children)})"
    )

    # as much as i'd like to keep the nodes, i don't think it's possible.
    # nodes seem to be opaque to the user from the tree-sitter interface?

    # we already have unique sets, each key is allowed only once
    sections = []
    for rent in parents:
        # get unique offsets between parent and first child
        children = list(parents.get(rent, set()))  # use key to get children
        first_child = children[0] if children else None  # only first child
        if first_child:  # parent must have children
            # extract the slice
            start_byte = rent.start_byte  # start at parent
            end_byte = first_child.start_byte  # stop at first child
            text = rent.text[start_byte:end_byte].decode()  # maybe just bytes?
            # do not append empty chunks
            # do not append parents, we have children already
            # we only want unique slices from parents
            if text:
                # this should fill the gap and provide
                # missing information unique to parents
                sections.append(
                    (
                        start_byte,
                        end_byte,
                        rent,
                        first_child,
                        text,
                    )
                )
        # now we can get the slices from the children
        for child in children:
            # get the full section from the child nodes
            # these are usually small, but occassionaly can be +10k bytes
            # we want 5k bytes or less to keep chunks reasonable
            sections.append(
                (
                    child.start_byte,
                    child.end_byte,
                    rent,
                    child,
                    child.text.decode(),
                )
            )
    # the dictionary is unordered
    sections = sorted(sections, key=lambda s: s[0])

    # I still get duplicates because some children are parents and others are not.
    # This is arbitrary, not sure if there's a finite way to go about this to
    # enable general consumption.
    # Sometimes we end up with duplicates, which means that we most likely have
    # a child that is a parent which means we should be able to extract those,
    # but the above algorithms do not account for that.
    # so, parent -> child -> descendent -> [children]
    # parsing out the dom for unique nodes is a royal pain in the ass.
    # especially considering tree-siter was not designed for this at all.
    print(cs.paint(f"Extracted {len(sections)} sections.", fg=cs.Code.YELLOW))
    for i, sec in enumerate(sections):
        start = sec[0]
        end = sec[1]
        text = sec[-1].strip()
        head = cs.paint(f"--- section[{i}] has {end - start} bytes ---", fg=cs.Code.RED)
        print(head)
        print(text[: args.margin])  # just do the first n bytes
