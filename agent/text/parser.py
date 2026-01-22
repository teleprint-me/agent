# agent/text/parser.py
"""
Copyright (C) 2023 Austin Berrio

A tiny, standalone language parser that splits a source file into semantic "chunks":
  - consecutive import/include directives
  - function definitions
  - struct/enum/typedef definitions
  - everything else (globals, macros, …)
"""

from argparse import ArgumentParser
from pathlib import Path
from typing import Iterable, List, Set

from tree_sitter import Node, Tree

from agent.text.sitter import TextSitter

# If you want to add a new grammar (e.g. Go, TS, etc), just add its import node type
# to one of the appropriate sets below. New sets can be added on as needed basis.

# docstrings are a `Node.type` classified as "expression_statement".
# docstrings are techinically considered to be literal strings and not a comment type.
# note that expression statements typically happen outside of a block area.
COMMENT_TYPES: Set[str] = {
    "comment",
    "line_comment",
}

# What counts as an “import” in the languages we support
IMPORT_TYPES: Set[str] = {
    "import_statement",  # Python, JS, etc.
    "import_from_statement",  # Python
    "preproc_include",  # C, C++, etc.
    "use_declaration",  # Rust
}

EXPRESSION_TYPES: Set[str] = {
    "expression_statement",
    "variable_assignment",
    "command",
}

CAPTURE_TYPES: Set[str] = COMMENT_TYPES | IMPORT_TYPES | EXPRESSION_TYPES


# Chunker
def chunk_tree(tree: Tree) -> Iterable[str]:
    """Yield the raw source text of each *semantic* chunk."""

    comments: List[str] = []
    imports: List[str] = []
    expressions: List[str] = []

    # iterate over the top‑level nodes of a tree
    for node in tree.root_node.children:
        # --- extract node text ---

        # Decode current node
        txt = node.text.decode()
        # Peek into next node
        nxt = node.next_sibling
        # Peek at prev node
        prv = node.prev_sibling

        # --- handle semicolons ---

        # Skip semicolons
        if node.type == ";":
            continue
        # Merge split nodes
        if nxt and nxt.type == ";":
            txt += nxt.text.decode()
            yield txt
            continue

        # --- handle comments ---

        # Merge and flush accumulated comments
        if node.type in COMMENT_TYPES:
            comments.append(txt.strip())
            continue
        if comments:
            yield "\n".join(comments)
            comments.clear()

        # --- handle imports ---

        # Merge and flush accumulated imports
        if node.type in IMPORT_TYPES:
            imports.append(txt.strip())
            continue
        if imports:
            yield "\n".join(imports)
            imports.clear()

        # --- handle expressions ---

        # Merge flat expressions
        if node.type in EXPRESSION_TYPES:
            expressions.append(txt.strip())
            continue
        if expressions:
            yield "\n".join(expressions)
            expressions.clear()

        # Yield the node as a separate chunk
        yield txt

    # --- Flush remaining buckets (if any) ---

    if comments:
        yield "\n".join(comments)
    if imports:
        yield "\n".join(imports)
    if expressions:
        yield "\n".join(expressions)


# Main CLI
if __name__ == "__main__":  # pragma: no cover
    from argparse import ArgumentParser, Namespace

    def parse_args() -> Namespace:
        parser = ArgumentParser(
            description="Parse a source file with tree-sitter and chunk it"
        )
        parser.add_argument(
            "path",
            help="Path to a supported source file",
        )
        parser.add_argument(
            "-p",
            "--pretty-print",
            action="store_true",
            help="Pretty print the source tree.",
        )
        return parser.parse_args()

    def chunk(tree: Tree) -> None:
        for i, chunk in enumerate(chunk_tree(tree), 1):
            print(f"--- CHUNK {i} ---")
            print(chunk.strip())
            print()

    args = parse_args()

    tree = TextSitter.tree(args.path)
    if tree is None:
        print(
            "Could not parse - unsupported language or missing parser.",
            file=sys.stderr,
        )
        sys.exit(1)

    if args.pretty_print:
        TextSitter.pretty_print(tree.root_node)
    else:
        chunk(tree)
