# agent/parser/loader.py
"""
Utilities for loading Tree-Sitter languages, parsers, and trees.

Public helpers
--------------
* :func:`get_language` - Return a :class:`tree_sitter.Language` instance for a file.
* :func:`get_parser`   - Return a fresh :class:`tree_sitter.Parser` configured for the file.
* :func:`get_tree`     - Convenience: parse a file and return a :class:`tree_sitter.Tree`.

All helpers are lightweight and cache the immutable `Language` objects
internally via :func:`functools.lru_cache`.
"""

import importlib
import importlib.metadata
import importlib.util
import sys
from functools import lru_cache
from pathlib import Path
from typing import Any, Optional, Union

# `tree_sitter` 2.x+ ships a C extension that exposes a `language()` function.
# The return value is a PyCapsule (a `void *`).  In CPython 3.13+ that type is
# called `types.CapsuleType`; for older versions we fall back to `any`.
try:
    from types import CapsuleType  # type: ignore[attr-defined]  # 3.13+
except (ModuleNotFoundError, ImportError):  # pragma: no cover
    CapsuleType = Any  # type: ignore[assignment]

from tree_sitter import Language, Parser, Tree

# Extension: tree-sitter package name mapping
# Note: Markdown & LaTeX are not supported by tree-sitter.
_PKG_TO_EXT: dict[str, set[str]] = {
    "bash": {".sh"},
    "c": {".c", ".h"},
    "cpp": {".cc", ".cpp", ".hpp"},
    "css": {".css"},
    "html": {".htm", ".html"},
    "javascript": {".js", ".mjs"},
    "json": {".json"},
    "markdown": {".md"},
    "python": {".py", ".pyi"},
    "rust": {".rs"},
}

_EXT_TO_PKG: dict[str, str] = {}
for _k, _v in _PKG_TO_EXT.items():
    for _ext in _v:
        _EXT_TO_PKG[_ext] = _k

_MODULE_NAMES = []
for _d in importlib.metadata.distributions():
    if _d.name.startswith("tree-sitter-"):
        _MODULE_NAMES.append(_d.name)


@lru_cache(maxsize=None)
def _capsule_from_name(lang: str) -> CapsuleType:
    """
    Import `lang` and return the `language()` capsule.

    Returns: CapsuleType | None
        The PyCapsule that :class:`tree_sitter.Language` expects, or
        `None` if the module cannot be imported or does not expose
        `language()`.

    Raises ModuleNotFoundError if the module does not exist.
    Raises AttributeError if the API contract is broken.
    """
    module = importlib.import_module(f"tree_sitter_{lang}")
    return module.language()


@lru_cache(maxsize=None)
def _capsule_from_path(name: Union[str, Path]) -> CapsuleType:
    """
    Import `name` and return the `language()` capsule.

    Returns: CapsuleType | None
        The PyCapsule that :class:`tree_sitter.Language` expects, or
        `None` if the module cannot be imported or does not expose
        `language()`.

    Raises ModuleNotFoundError if the module does not exist.
    Raises AttributeError if the API contract is broken.
    """
    suffix = Path(name).suffix.lower()
    lang = _EXT_TO_PKG.get(suffix)
    if not lang:
        raise ValueError(
            f"Unsupported file extension '{suffix}'. "
            "Supported extensions are: {sorted(_PKG_TO_EXT.keys())}"
        )
    return _capsule_from_name(lang)


@lru_cache(maxsize=None)
def get_language(cls: Union[str, Path]) -> Language:
    """
    Return a :class:`tree_sitter.Language` instance.

    The function is idempotent: repeated calls for the same language
    reuse the cached `Language` object.
    """
    if Path(cls).is_file():
        capsule = _capsule_from_path(cls)
        return Language(capsule)
    capsule = _capsule_from_name(cls)
    return Language(capsule)  # note: capsule type is void*


def get_parser(cls: Union[str, Path]) -> Parser:
    """
    Create a fresh :class:`tree_sitter.Parser` for a language.

    A new `Parser` instance is returned each time - this is intentional
    because parsers hold mutable state that is useful when editing a file
    incrementally.
    """
    language = get_language(cls)
    return Parser(language)


def get_tree(cls: Union[str, Path], name: Optional[Union[str, Path]] = None) -> Tree:
    """
    Parse *cls* if it is a file path; otherwise treat it as a language name and parse *name*.

    Raises ValueError when neither `cls` nor `name` point to an existing source file,
    or when the language for that file cannot be found.
    """
    p_cls = Path(cls)
    if p_cls.is_file():
        parser = get_parser(p_cls)
        return parser.parse(p_cls.read_bytes())

    # cls is a language identifier – we need the file to parse
    if not name or not Path(name).is_file():  # <- guard against None / missing file
        raise ValueError(
            f"Expected `name` to be an existing source file when `cls={cls}` "
            "doesn't point at one."
        )

    parser = get_parser(cls)
    return parser.parse(Path(name).read_bytes())


# Public API
__all__ = ["get_language", "get_parser", "get_tree"]

# example usage
if __name__ == "__main__":
    from argparse import ArgumentParser, Namespace

    def parse_args() -> Namespace:
        parser = ArgumentParser(description="Parse a source file with tree-sitter.")
        parser.add_argument("path", help="Path to a plain text source file")
        return parser.parse_args()

    def walk(root: Node, depth: int = 0, margin: int = 30) -> None:
        """Pretty-print a small subtree."""
        indent = "  " * depth
        txt = root.text[:margin].decode("utf8", errors="replace")
        print(f"{indent}{root.type:2} ({txt!r})")
        for node in root.children:
            walk(node, depth + 1)

    args = parse_args()

    tree = get_tree(args.path)

    # note: language.version is deprecated. use language.abi_version instead.
    # a warning will be emitted to standard output if version is used.
    print(f"Language Name: {tree.language.name}")
    print(f"ABI Version: {tree.language.abi_version}")

    walk(tree.root_node)
