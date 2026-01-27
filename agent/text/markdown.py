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

        # oh my fucking god, it's finally working 🥲
        # finally. this problem nearly drove me mad.
        # Algorithm: For each section node, gather its child nodes.
        # Then accumulate contiguous ranges until sum > max_chunk.
        # When sum > max_chunk, finalize slice up to before the last
        # child that would exceed. Then start new slice from that child.
        # note: this can probably be simplified, but this problem is non-trivial.

        # Split into < max_chunk chunks
        if raw_size >= max_chunk:
            # We only want to parse nodes that are leaves (omit sections)
            if any(c.type == "section" for c in node.children):
                continue  # skip parent - parse children first

            # Current node is not a parent of any existing section nodes.

            # Get a TreeCursor to walk siblings (this is a recursive op)
            cursor = node.walk()  # cursor starts at current section
            # Get the first descendant
            cursor.goto_first_child()  # i.e. section -> atx_heading

            # Create a buffer to group siblings together
            buffer = []  # i.e. pipe_tables have pipe_table_* neighbors

            # Discover and pool siblings that are < max_chunk
            while True:
                sib = cursor.node  # update current sibling

                # Leaves only - no sections.
                if any(c.type == "section" for c in sib.children):
                    break  # skip parent - parse children first

                # If the sibling is a blob, go to its first child
                if ts.size(sib) > max_chunk:
                    cursor = sib.walk()  # update cursor to isolate blob
                    cursor.goto_first_child()  # get first child
                    continue  # recurse until size < max_chunk

                # Skip empty / whitespace‑only parts
                if not ts.text(sib):  # strip and decode
                    continue

                buffer.append(sib)  # accumulate
                buffer_text = "\n".join((s.text.decode() for s in buffer))
                buffer_size = len(buffer_text)
                if buffer_size >= max_chunk:
                    temp = []  # mitigate overflow
                    while buffer_size >= max_chunk:
                        temp.append(buffer.pop())  # popping inverts order
                        buffer_text = "\n".join((s.text.decode() for s in buffer))
                        buffer_size = len(buffer_text)

                    # Create a slice relative to the current range
                    slices.append(
                        NodeSlice(
                            start=buffer[0].start_byte,  # parent start
                            end=buffer[-1].end_byte,  # parent end
                            size=buffer_size,  # n bytes in slice
                            node=sib.parent,  # common ancestor
                            text=buffer_text.encode(),  # raw bytes
                        )
                    )

                    # update accumulation and restore order
                    buffer = list(reversed(temp))

                # This has to be done last. Otherwise, nodes are skipped
                if not cursor.goto_next_sibling():
                    break

    # deterministic order
    slices.sort(key=lambda s: s.start)
    return slices


def sample_slice(slice: NodeSlice, window: int = 30) -> str:
    text = slice.text.decode(errors="replace").strip()
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
