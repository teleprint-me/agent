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

from agent.text import sitter

# What counts as an “import” in the languages we support
# If you add a new grammar (e.g. Rust, Go, JS) just add its import node type
# to the set below.
IMPORT_TYPES: Set[str] = {
    "import_statement",  # Python, JS, TS, etc.
    "import_from_statement",  # Python
    "preproc_include",  # C, C++, Swift, etc.
    "use_declaration",  # Rust
}

# docstrings are type "expression_statement".
# this means expression_statement has multiple meanings and can potentially conflict based on context.
# not sure if it's a good idea to add here. probably not.
# note that expression statements typically happen outside of a block area.
COMMENT_TYPES: Set[str] = {
    "comment",
    "line_comment",
}

EXPRESSION_TYPES: Set[str] = {
    "expression_statement",
    "variable_assignment",
    "command",
}


# Utility: iterate over the top‑level nodes of a tree
def top_level_nodes(tree: Tree) -> Iterable[Node]:
    """
    Yield the children of the root node (e.g. `module` in Python, `source_file` in C).
    """
    return tree.root_node.children


# Chunker
def chunk_tree(tree: Tree) -> Iterable[str]:
    """Yield the raw source text of each *semantic* chunk."""

    import_bucket: List[str] = []
    comment_bucket: List[str] = []
    expr_bucket: List[str] = []

    for node in top_level_nodes(tree):
        # --- extract node text ---

        # Decode current node
        txt = node.text.decode()
        # Peek into next node
        nxt = node.next_sibling

        # --- handle semicolons ---

        # Skip semicolons and join split nodes
        if node.type == ";":
            continue
        if nxt and nxt.type == ";":
            txt += nxt.text.decode()
            yield txt
            continue

        # --- handle comments ---

        # Merge and flush accumulated comments
        if node.type in COMMENT_TYPES:
            comment_bucket.append(txt.strip())
            continue
        if comment_bucket:
            yield "\n".join(comment_bucket)
            comment_bucket.clear()

        # --- handle imports ---

        # Merge and flush accumulated imports
        if node.type in IMPORT_TYPES:
            import_bucket.append(txt.strip())
            continue
        if import_bucket:
            yield "\n".join(import_bucket)
            import_bucket.clear()

        # --- handle expressions ---

        # Merge flat expressions
        if node.type in EXPRESSION_TYPES:
            expr_bucket.append(txt.strip())
            continue
        if expr_bucket:
            yield "\n".join(expr_bucket)
            expr_bucket.clear()

        # Yield the node as a separate chunk
        yield txt

    # --- Flush remaining buckets (if any) ---

    if comment_bucket:
        yield "\n".join(comment_bucket)
    if import_bucket:
        yield "\n".join(import_bucket)
    if expr_bucket:
        yield "\n".join(expr_bucket)


# Main CLI
if __name__ == "__main__":  # pragma: no cover
    from argparse import ArgumentParser, Namespace

    def parse_args() -> Namespace:
        parser = ArgumentParser(
            description="Parse a source file with tree‑sitter and chunk it"
        )
        parser.add_argument(
            "path",
            help="Path to a supported source file",
        )
        parser.add_argument(
            "--walk",
            action="store_true",
            help="Pretty print the source tree.",
        )
        return parser.parse_args()

    def walk(root: Node, depth: int = 0, margin: int = 30) -> None:
        """Pretty-print a small subtree."""
        indent = "  " * depth
        txt = root.text[:margin].decode("utf8", errors="replace")
        print(f"{indent}{root.type:2} ({txt!r})")
        for node in root.children:
            walk(node, depth + 1)

    def chunk(tree: Tree) -> None:
        for i, chunk in enumerate(chunk_tree(tree), 1):
            print(f"--- CHUNK {i} ---")
            print(chunk.strip())
            print()

    args = parse_args()

    tree = sitter.get_tree(args.path)
    if tree is None:
        print(
            "Could not parse – unsupported language or missing parser.", file=sys.stderr
        )
        sys.exit(1)

    if args.walk:
        walk(tree.root_node)
    else:
        chunk(tree)
