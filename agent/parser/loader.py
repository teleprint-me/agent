"""
agent.parser.loader
Attempt to guess, load, and return a tree-sitter parser.
"""

import importlib
import importlib.metadata
import importlib.util
import sys
from pathlib import Path
from functools import lru_cache

# Python 3.13+ deprecated the majority of aliases in favor of `GenericAlias`.
# For simplicity, use the base builtin types.
# i.e. Use `any` instead of `Any`, `list` instead of `List`, etc.
from typing import Optional, Union

# `tree_sitter` 2.x+ ships a C extension that exposes a `language()` function.
# The return value is a PyCapsule (a `void *`).  In CPython 3.13+ that type is
# called `types.CapsuleType`; for older versions we fall back to `any`.
try:
    from types import CapsuleType  # type: ignore[attr-defined]  # 3.13+
except (ModuleNotFoundError, ImportError):
    CapsuleType = any  # type: ignore[assignment]

from tree_sitter import Language, Parser, Tree

# tree-sitter package name mapping, e.g. tree-sitter-c
# note: markdown and latex are not supported by tree-sitter
EXT_TO_PKG = {
    ".c": "c",
    ".h": "c",
    ".cpp": "cpp",
    ".hpp": "cpp",
    ".rs": "rust",
    ".py": "python",
    ".sh": "bash",
    ".html": "html",
    ".css": "css",
    ".js": "javascript",
}


def guess_module_name(path: Union[str, Path]) -> Optional[str]:
    suffix = Path(path).suffix.lower()
    name = EXT_TO_PKG.get(suffix)
    if name is None:
        return None
    return f"tree_sitter_{name}"


@lru_cache(maxsize=None)
def guess_language_capsule(name: str) -> Optional[CapsuleType]:
    if name is None:
        return None  # unsupported language

    try:
        module = importlib.import_module(name)
    except ImportError:
        return None

    # https://docs.python.org/3/c-api/capsule.html
    # https://docs.python.org/3/extending/extending.html#using-capsules
    return module.language()  # returns a PyCapsule object (e.g. void*)


def parse_file(source: Union[str, Path]) -> Optional[Tree]:
    path = Path(source)
    if not path.is_file():
        return None  # not a source file

    name = guess_module_name(path)
    capsule = guess_language_capsule(name)
    if capsule is None:
        return None  # unsupported language

    language = Language(capsule)
    parser = Parser(language)
    return parser.parse(path.read_bytes())


# example usage
if __name__ == "__main__":
    from argparse import ArgumentParser

    parser = ArgumentParser(description="Parse a source file with tree‑sitter.")
    parser.add_argument("path", help="Path to a plain text source file")
    args = parser.parse_args()

    tree = parse_file(args.path)
    if tree is None:
        print("Could not parse the file - unsupported language or missing parser.")
        sys.exit(1)

    print(tree)
    for node in tree.root_node.children:
        print(node)
