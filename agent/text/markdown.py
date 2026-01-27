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
        first_child = next((c for c in node.children if c.type == "section"), None)
        # Slice from top of parent to top of child, else use current node
        end_byte = first_child.start_byte if first_child else node.end_byte

        # Slice from the absolute source
        raw = src[node.start_byte : end_byte]
        # Skip empty / whitespace‑only headers
        if not raw.decode(errors="replace").strip():
            continue
        # Get the size of the current chunk
        raw_size = len(raw)

        # Chunk is within the given range
        if raw_size < max_chunk:
            slice = NodeSlice(
                start=node.start_byte,
                end=end_byte,
                size=raw_size,
                node=node,
                text=raw,
            )
            slices.append(slice)
            print_slice(slice)

        # Split into < max_chunk chunks
        if raw_size >= max_chunk:
            # Simplify: For each section node, gather its child nodes
            # (including nested sections - maybe?). Then accumulate contiguous
            # ranges until sum > max_chunk. When sum > max_chunk, finalize
            # slice up to before the last child that would exceed. Then
            # start new slice from that child.

            # grab the current node
            descendant = first_child if first_child else node

            chunk_start = node.start_byte
            chunk_size = 0

            # use descendants to discover chunk boundaries
            for child in descendant.children:
                # stop when we reach the first nested section (header ends there)
                if child.type == "section":
                    break
                part = raw[chunk_start : child.end_byte]
                slice = NodeSlice(
                    start=chunk_start,
                    end=child.end_byte,
                    size=len(part),
                    node=child,
                    text=part,
                )
                slices.append(slice)
                print_slice(slice)
                # update cursor position
                chunk_start = child.end_byte

    # deterministic order
    slices.sort(key=lambda s: s.start)
    return slices


def print_node(node: Node, start_byte: int, end_byte: int):
    size = end_byte - start_byte
    text = node.text[start_byte:end_byte]
    print(
        cs.paint(f"({node.type})", cs.Code.YELLOW),
        cs.paint(f"({start_byte, end_byte})", cs.Code.WHITE),
        cs.paint(f"{size} bytes", cs.Code.RED),
        cs.paint(f"{text!r}", cs.Code.GREEN),
    )


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

    # print(
    #     f"document: {tree.root_node.end_byte} bytes, extracted {len(slices)} header slices"
    # )
    # for s in slices:
    #     print_slice(s, args.preview)
    #     text = s.text.decode(errors="replace").strip()
    #     print(text[: args.margin] if args.margin > 0 else text)
