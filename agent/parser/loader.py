# agent/parser/loader.py
"""
Utilities for dynamically loading a Tree‑Sitter parser and parsing a
source file.

The module exposes a single public helper – :func:`parse_file`.  All other
functions are implementation details and are not exported.

Typical usage:

>>> tree = parse_file("src/main.c")
>>> if tree is None:  # unsupported language or missing parser
...     ...

The function returns a :class:`tree_sitter.Tree` or `None`.
"""

import importlib
import importlib.metadata
import importlib.util
import sys
from pathlib import Path
from functools import lru_cache
from typing import Any, Optional, Union

# `tree_sitter` 2.x+ ships a C extension that exposes a `language()` function.
# The return value is a PyCapsule (a `void *`).  In CPython 3.13+ that type is
# called `types.CapsuleType`; for older versions we fall back to `any`.
try:
    from types import CapsuleType  # type: ignore[attr-defined]  # 3.13+
except (ModuleNotFoundError, ImportError):  # pragma: no cover
    CapsuleType = Any  # type: ignore[assignment]

from tree_sitter import Language, Parser, Tree

# Extension: tree‑sitter package name mapping
# Note: Markdown & LaTeX are not supported by tree‑sitter.
_EXT_TO_PKG = {
    ".c": "c",
    ".h": "c",
    ".cpp": "cpp",
    ".hpp": "cpp",
    ".rs": "rust",
    ".py": "python",
    ".sh": "bash",
    ".md": "markdown",
    ".json": "json",
    ".html": "html",
    ".css": "css",
    ".js": "javascript",
}


def _module_name_for_path(path: Union[str, Path]) -> Optional[str]:
    """
    Convert a file path into the name of the tree‑sitter package
    that implements the language.

    Parameters
    ----------
    path
        Path to a source file.

    Returns
    -------
    str | None
        The import‑able package name (e.g. `"tree_sitter_c"`) or
        `None` if the extension is unknown.
    """
    suffix = Path(path).suffix.lower()
    pkg = _EXT_TO_PKG.get(suffix)
    return f"tree_sitter_{pkg}" if pkg else None


@lru_cache(maxsize=None)
def _capsule_for_name(name: str) -> Optional[CapsuleType]:
    """
    Import `name` and return the `language()` capsule.

    Parameters
    ----------
    name
        Importable module name, e.g. `"tree_sitter_c"`.  Must be
        non‑empty.

    Returns
    -------
    CapsuleType | None
        The PyCapsule that :class:`tree_sitter.Language` expects, or
        `None` if the module cannot be imported or does not expose
        `language()`.
    """
    try:
        module = importlib.import_module(name)
    except ImportError:
        return None

    # The C extension always provides a `language()` function.
    return getattr(module, "language", lambda: None)()


@lru_cache(maxsize=None)
def get_language(path: Union[str, Path]) -> Optional[Language]:
    module_name = _module_name_for_path(path)
    if not module_name:
        return None
    capsule = _capsule_for_name(module_name)
    if capsule is None:
        return None
    return Language(capsule) # note: type is void*


def get_parser(path: Union[str, Path]) -> Optional[Parser]:
    language = get_language(path)
    if language is None:
        return None
    return Parser(language)


def get_tree(path: Union[str, Path]) -> Optional[Tree]:
    path = Path(path)
    if not path.is_file():
        return None

    parser = get_parser(path)
    if parser is None:
        return None

    try:
        return parser.parse(path.read_bytes())
    except OSError:  # e.g. permission denied, vanished, etc.
        return None


# Public API
__all__ = ["get_language", "get_parser", "get_tree"]

# example usage
if __name__ == "__main__":
    from argparse import ArgumentParser

    parser = ArgumentParser(description="Parse a source file with tree‑sitter.")
    parser.add_argument("path", help="Path to a plain text source file")
    args = parser.parse_args()

    tree = get_tree(args.path)
    if tree is None:
        print("Could not parse the file - unsupported language or missing parser.")
        sys.exit(1)

    print(tree)
    for node in tree.root_node.children:
        print(node)
