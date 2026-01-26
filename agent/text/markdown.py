# agent/text/markdown.py
"""
Markdown section extractor that returns the *header* part of every
`section` node (i.e. the part that belongs to the parent but not to
any nested section).

The algorithm walks the tree once, keeps the original `Node` for
metadata, and yields a `NodeSlice` that contains the absolute byte
range and the extracted text.

Authors:
  - Austin Berrio
  - GPT-OSS 20B
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, List

from tree_sitter import Node, Tree

from agent.text import color as cs
from agent.text.sitter import TextSitter as ts


@dataclass(frozen=True)
class NodeSlice:
    start: int  # absolute byte offset
    end: int  # absolute byte offset (exclusive)
    size: int  # end - start
    node: Node  # the `section` node that owns the slice
    text: bytes  # raw bytes - keep as bytes for later processing


# --------------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------------- #
def walk_sections(tree: Tree, max_chunk: int = 5_000) -> List[NodeSlice]:
    """
    Return a list of NodeSlice objects for every section node.

    * `max_chunk` controls the maximum size of a single slice.  If a
      header is larger, it is split into multiple NodeSlice objects.
    """
    src = tree.root_node.text  # the full source as bytes
    slices: List[NodeSlice] = []

    for node in ts.walk(tree.root_node):
        if node.type != "section":
            continue

        # Find the first nested section child (if any)
        first_child = next(
            (c for c in node.children if c.type == "section"),
            None,
        )

        header_end = first_child.start_byte if first_child else node.end_byte
        if header_end <= node.start_byte:
            continue  # defensive - should not happen

        # Slice from the absolute source
        raw = src[node.start_byte : header_end]
        if not raw.strip():  # skip empty / whitespace‑only headers
            continue

        # Split into < max_chunk chunks if needed
        for i in range(0, len(raw), max_chunk):
            part = raw[i : i + max_chunk]
            slices.append(
                NodeSlice(
                    start=node.start_byte + i,
                    end=node.start_byte + i + len(part),
                    size=len(part),
                    node=node,
                    text=part,
                )
            )

    # deterministic order
    slices.sort(key=lambda s: s.start)
    return slices


def print_slice(slice: NodeSlice, margin: int = 30) -> None:
    """Pretty-print a NodeSlice (header)."""
    txt_preview = slice.text.decode(errors="replace")[:margin]
    print(
        cs.paint(f"({slice.node.type})", cs.Code.YELLOW),
        cs.paint(f"({slice.start}, {slice.end})", cs.Code.WHITE),
        cs.paint(f"{slice.size} bytes", cs.Code.RED),
        cs.paint(f"{txt_preview!r}", cs.Code.GREEN),
    )


# --------------------------------------------------------------------------- #
# CLI
# --------------------------------------------------------------------------- #
if __name__ == "__main__":  # pragma: no cover
    import argparse

    parser = argparse.ArgumentParser(
        description="Extract markdown section headers (header-only slices)"
    )
    parser.add_argument("path", help="Path to a markdown file")
    parser.add_argument(
        "-p",
        "--preview",
        type=int,
        default=30,
        help="Number of bytes to show for each slice (default: 30)",
    )
    parser.add_argument(
        "-m",
        "--margin",
        type=int,
        default=100,
        help="Number of bytes to show for each chunk (default: 30)",
    )
    parser.add_argument(
        "-c",
        "--chunk",
        type=int,
        default=5_000,
        help="Maximum slice size in bytes (default: 5 kB)",
    )
    args = parser.parse_args()

    src_bytes = Path(args.path).read_bytes()
    tree = ts.tree("markdown", src_bytes)

    slices = walk_sections(tree, max_chunk=args.chunk)

    print(
        f"document: {tree.root_node.end_byte} bytes, extracted {len(slices)} header slices"
    )
    for s in slices:
        print_slice(s, args.preview)
        text = s.text.decode(errors="replace").strip()
        print(text[: args.margin] if args.margin > 0 else text)
