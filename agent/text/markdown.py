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
        child = next((c for c in node.children if c.type == "section"), None)

        # Slice from top of parent to top of child
        start_byte = node.start_byte  # top of parent
        end_byte = child.start_byte if child else node.end_byte  # top of child

        # Slice from the absolute source
        raw = src[node.start_byte : end_byte]
        # Compute size of raw source
        raw_size = len(raw)

        # Skip empty / whitespace‑only headers
        if not raw.decode(errors="replace").strip():
            continue

        # Chunk is within the given range
        if raw_size < max_chunk:
            slice = NodeSlice(
                start=start_byte,
                end=end_byte,
                size=raw_size,
                node=node,
                text=raw,
            )
            slices.append(slice)

        # This problem is literally driving me crazy.

        # Split into < max_chunk chunks
        if raw_size >= max_chunk:
            # Simplify: For each section node, gather its child nodes
            # (including nested sections - maybe?). Then accumulate contiguous
            # ranges until sum > max_chunk. When sum > max_chunk, finalize
            # slice up to before the last child that would exceed. Then
            # start new slice from that child.

            # We only want to parse leaves that have children (omit sections)
            if any(c.type == "section" for c in node.children):
                continue  # skip parent - parse children first

            # Current node is a section and has no child sections.
            chunk_start = start_byte
            chunk_size = 0

            # Split into < max_chunk chunks if needed
            for c in node.children:
                if chunk_size < max_chunk:
                    chunk_size += c.end_byte - c.start_byte
                    continue  # accumulate

                # Extract resized chunk
                part = src[chunk_start : c.end_byte]
                # Skip empty / whitespace‑only parts
                if not part.decode(errors="replace").strip():
                    continue

                # For an unknown reason, large chunks are not properly split.
                # Still results in large blobs. For example, 12839 bytes should
                # result in 3 (12839 / 5000 = 2r1) parts, but results in 1 large
                # part instead. This algorithm is close, but not there yet.
                slice = NodeSlice(
                    start=chunk_start,
                    end=c.end_byte,
                    size=len(part),
                    node=node,
                    text=part,
                )
                slices.append(slice)

                # Update and reset
                chunk_start = c.end_byte
                chunk_size = 0

    # deterministic order
    slices.sort(key=lambda s: s.start)
    return slices


def sample_slice(slice: NodeSlice, window: int = 30) -> str:
    text = slice.text.decode(errors="replace")
    return text[:window] if window > 0 else text


def print_slice(slice: NodeSlice, preview: int = 30) -> None:
    """Pretty-print a NodeSlice (header)."""
    text = sample_slice(slice, window=preview)
    print(
        cs.paint(f"({slice.node.type})", cs.Code.YELLOW),
        cs.paint(f"({slice.start}, {slice.end})", cs.Code.WHITE),
        cs.paint(f"{slice.size} bytes", cs.Code.RED),
        cs.paint(f"{text!r}", cs.Code.GREEN),
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
        help="Number of bytes previewed from each node (default: 30)",
    )
    parser.add_argument(
        "-s",
        "--sample",
        type=int,
        default=100,
        help="Number of bytes sampled from each chunk (default: 100)",
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
        print(sample_slice(s, args.sample))
