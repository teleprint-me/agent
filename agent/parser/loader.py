# agent/parser/loader.py
"""
Utilities for loading Tree‑Sitter languages, parsers, and trees.

Public helpers
--------------
* :func:`get_language` – Return a :class:`tree_sitter.Language` instance for a file.
* :func:`get_parser`   – Return a fresh :class:`tree_sitter.Parser` configured for the file.
* :func:`get_tree`     – Convenience: parse a file and return a :class:`tree_sitter.Tree`.

All helpers are lightweight and cache the immutable `Language`` objects
internally via :func:`functools.lru_cache`.
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
    """
    Return a :class:`tree_sitter.Language` instance for *path*.

    The function is idempotent: repeated calls for the same language
    reuse the cached `Language` object.
    """
    module_name = _module_name_for_path(path)
    if not module_name:
        return None
    capsule = _capsule_for_name(module_name)
    if capsule is None:
        return None
    return Language(capsule) # note: type is void*


def get_parser(path: Union[str, Path]) -> Optional[Parser]:
    """
    Create a fresh :class:`tree_sitter.Parser` for the language of *path*.

    A new `Parser` instance is returned each time – this is intentional
    because parsers hold mutable state that is useful when editing a file
    incrementally.
    """
    language = get_language(path)
    if language is None:
        return None
    return Parser(language)


def get_tree(path: Union[str, Path]) -> Optional[Tree]:
    """
    Parse *path* and return a :class:`tree_sitter.Tree`.

    The function silently returns `None` for unsupported files or
    missing language packages.  It reads the file *once* and feeds the raw
    bytes to the parser.
    """
    p = Path(path)
    if not p.is_file():
        return None

    parser = get_parser(p)
    if parser is None:
        return None

    try:
        return parser.parse(p.read_bytes())
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
