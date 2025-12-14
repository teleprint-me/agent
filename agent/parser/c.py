# agent/parser/c.py
"""
A tiny, standalone language parser that splits a source file into semantic "chunks":
  - consecutive import/include directives
  - function definitions
  - struct/enum/typedef definitions
  - everything else (globals, macros, …)
"""

from argparse import ArgumentParser
from pathlib import Path
from typing import Iterable, List, Set

from agent.parser import loader
from tree_sitter import Node, Tree

# What counts as an “import” in the languages we support
# If you add a new grammar (e.g. Rust, Go, JS) just add its import node type
# to the set below.
IMPORT_TYPES: Set[str] = {
    "import_statement",  # Python, JS, TS, etc.
    "import_from_statement",  # Python
    "preproc_include",  # C, C++, Swift, etc.
    "use_declaration",  # Rust
    "import_declaration",  # Go
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
        # print(f"--- node type: {node.type} ---")  # debug

        # --- handle semicolons ---

        # Skip semicolons that the grammar has turned into a separate node.
        if node.type == ";":
            continue

        # Join split nodes when a semicolon is an individual node
        txt = node.text.decode()
        nxt = node.next_sibling
        if nxt and nxt.type == ";":
            txt += nxt.text.decode()
            yield txt
            continue

        # --- handle comments ---

        # Merge comments
        if node.type == "comment" and nxt.type == "comment":
            comment_bucket.append(txt.strip())
            continue

        # Flush accumulated comments
        if comment_bucket:
            yield "\n".join(comment_bucket)
            comment_bucket.clear()

        # --- handle imports ---

        # Merge imports
        if node.type in IMPORT_TYPES:
            import_bucket.append(txt.strip())
            continue

        # Flush accumulated imports
        if import_bucket:
            yield "\n".join(import_bucket)
            import_bucket.clear()

        # --- handle expressions ---

        # Merge flat expressions
        if node.type == "expression_statement":
            expr_bucket.append(txt.strip())
            continue

        if expr_bucket:
            yield "\n".join(expr_bucket)
            expr_bucket.clear()

        # Yield the node as a separate chunk
        yield txt

    # --- Flush final buckets (if any) ---

    if comment_bucket:
        yield "\n".join(comment_bucket)

    if import_bucket:
        yield "\n".join(import_bucket)

    if expr_bucket:
        yield "\n".join(expr_bucket)


# Main CLI
if __name__ == "__main__":  # pragma: no cover
    ap = ArgumentParser(description="Parse a source file with tree‑sitter and chunk it")
    ap.add_argument("path", help="Path to a supported source file")
    args = ap.parse_args()

    tree = loader.get_tree(args.path)
    if tree is None:
        print(
            "Could not parse – unsupported language or missing parser.", file=sys.stderr
        )
        sys.exit(1)

    for i, chunk in enumerate(chunk_tree(tree), 1):
        print(f"--- CHUNK {i} ---")
        print(chunk.strip())
        print()
