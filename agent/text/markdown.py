# agent/text/markdown.py
"""
Markdown parsing helper built on top of :mod:`tree_sitter`.

The original version simply walked the tree and printed every `section` node.  That
resulted in overlapping, duplicate chunks - e.g., a heading with an H2 that also had
sub-headings would be emitted twice: once as its own section (the *outer* chunk)
and again for each nested header.

This refactor adds three high-level helpers:

`top_level_sections(tree)`
    Yield the text of every `section` node that does **not** have a parent
    `section`.  These are the outermost headings (H1/H2 …).

`leaf_sections(tree)`
    Yield sections with *no* nested section children - i.e., the most granular
    pieces.

`non_overlapping_sections(tree)`
    Sort all section nodes by start offset and skip any whose byte range lies
    completely inside a previously yielded one.  This gives you outer-most or
    inner-only sections depending on which ones are first in the file.

All helpers use :class:`agent.text.sitter.TextSitter` under the hood to keep the
public API tiny and easy to test.
"""

from __future__ import annotations

from pathlib import Path
from typing import Iterable, Tuple

from tree_sitter import Node, Tree

# Local imports - order matters for relative resolution in this repo.
try:  # pragma: no cover - defensive; the module is present during tests.
    from .sitter import TextSitter
except Exception as exc:  # pragma: no cover
    raise ImportError("agent.text.sitter must be available") from exc


# ---------------------------------------------------------------------------
# Basic node helpers - kept minimal for clarity.
# ---------------------------------------------------------------------------
class Markdown:
    """Convenience wrapper around :mod:`tree_sitter` specific to markdown."""

    @staticmethod
    def is_named(node: Node) -> bool:
        return node.is_named

    @staticmethod
    def is_document(node: Node) -> bool:
        # The root `document` node contains the entire file.  We usually skip it.
        return node.type == "document" or (
            node.parent and node.parent.type == "document"
        )

    @staticmethod
    def is_section(node: Node) -> bool:
        return node.type == "section"

    @staticmethod
    def text(node: Node) -> str:
        # `Node.text` returns raw bytes - decode as UTF-8.
        return node.text.decode("utf-8")

    @staticmethod
    def tree(path_or_data: str | bytes | Path) -> Tree:
        """
        Parse *path_or_data* into a :class:`tree_sitter.Tree` using the markdown language.

        Parameters
        ----------
        path_or_data : str|bytes|Path
            If `Path` or an existing file, read it.  Otherwise treat as raw source code.
        """
        path = Path(path_or_data)
        if path.is_file():
            path_or_data = path.read_bytes()
        # else assume str or bytes - `tree()` handles this internally.
        return TextSitter.tree("markdown", path_or_data)

    @staticmethod
    def walk(root: Node) -> Iterable[Node]:
        """
        Depth-first traversal that yields each node exactly once.
        Delegates to :class:`agent.text.sitter.TextSitter` for consistency.
        """
        return TextSitter.walk(root)

    # -----------------------------------------------------------------------
    # Extraction helpers - public API of this module.
    # -----------------------------------------------------------------------
    @staticmethod
    def top_level_sections(tree: Tree) -> Iterable[str]:
        """Yield text for every section that does **not** have a parent `section`.

        The iterator returns the *outermost* sections in file order - useful when you
        want an outline or high-level summary.
        """
        # i understand where GPT is coming from with this idea, but it doesn't work.
        # this will always return the root node because all child nodes will have
        # document as a parent node. All sub-sections will also be children of these
        # nodes. So on and so forth.
        root = tree.root_node
        for node in TextSitter.walk(root):
            if Markdown.is_section(node) and (
                not (node.parent and node.parent.type == "section")
            ):
                yield Markdown.text(node).strip()

    @staticmethod
    def leaf_sections(tree: Tree) -> Iterable[str]:
        """Yield text for every section that has **no** nested `section` children.

        These are the most granular pieces - e.g. each H3/H4 block with its own heading.
        """
        # this kind of works, but only yields the children of each parent resulting
        # in partial, incomplete, snippets. this is probably the most promising of
        # the 3 suggestions made by GPT.
        root = tree.root_node
        for node in TextSitter.walk(root):
            if Markdown.is_section(node) and not any(
                child.type == "section" for child in node.children
            ):
                yield Markdown.text(node).strip()

    @staticmethod
    def non_overlapping_sections(
        tree: Tree, *, include_inner: bool = True
    ) -> Iterable[str]:
        """
        Yield sections sorted by start offset while skipping any whose byte range is fully contained in a previously yielded section.

        Parameters
        ----------
        tree : Tree
            Parsed markdown document.
        include_inner : bool, default `True`
            If *False*, the function behaves like :func:`leaf_sections`; if *True*
            it yields the outermost sections first and discards nested ones.
        """
        # this function suffers from the same issue as `top_level_sections`.
        root = tree.root_node
        # Gather all (start,end,text) tuples for section nodes.
        chunks: list[Tuple[int, int, str]] = []
        for node in TextSitter.walk(root):
            if Markdown.is_section(node):
                start, end = node.byte_range
                text = Markdown.text(node).strip()
                chunks.append((start, end, text))
        # Sort by starting byte offset.
        chunks.sort(key=lambda t: t[0])

        covered_until = -1  # last end of a yielded section.
        for start, end, txt in chunks:
            if include_inner and start < covered_until:
                continue  # nested - skip it.
            yield txt
            if not include_inner:  # we are only interested in leaf nodes
                covered_until = max(covered_until, end)
            else:
                covered_until = max(covered_until, end)  # update for outermost logic


# ---------------------------------------------------------------------------
# Demo / CLI entry point - useful during development.
# ---------------------------------------------------------------------------
if __name__ == "__main__":  # pragma: no cover - manual testing only
    import argparse

    parser = argparse.ArgumentParser(description="Parse markdown and print sections")
    # GPT decided to have some fun with subparsers. Not necessary, but cool either way.
    subparsers = parser.add_subparsers(dest="cmd", required=True)

    p_top = subparsers.add_parser("top", help="Show top-level sections")
    p_leaf = subparsers.add_parser("leaf", help="Show leaf (deepest) sections")
    p_nonoverlap = subparsers.add_parser(
        "nonovlp",
        help="Show non-overlapping sections (outermost first)",
    )

    # i don't know why, but i love this.
    for sp in [p_top, p_leaf, p_nonoverlap]:
        sp.add_argument("path", type=str, help="Path to the markdown file")

    args = parser.parse_args()

    tree_obj = Markdown.tree(args.path)

    if args.cmd == "top":
        for i, sec in enumerate(Markdown.top_level_sections(tree_obj), 1):
            print(f"[{i}] {sec}...")
    elif args.cmd == "leaf":
        for i, sec in enumerate(Markdown.leaf_sections(tree_obj), 1):
            print(f"[{i}] {sec}...")
    else:  # nonovlp
        for i, sec in enumerate(
            Markdown.non_overlapping_sections(tree_obj, include_inner=True)
        ):
            print(f"[{i}] {sec}...")
