# agent/text/sitter.py
"""
Copyright (C) 2023 Austin Berrio

Utilities for loading Tree-Sitter languages, parsers, trees, queries, and captures.

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

from tree_sitter import Language, Parser, Query, QueryCursor, Tree

# Extension: tree-sitter package name mapping.
# Note: LaTeX is not supported by tree-sitter.
# there has to be a better way than this 🫠
_MOD_TO_EXT: dict[str, set[str]] = {
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
    "glsl": {
        ".glsl",  # generic
        ".shader",
        ".vert",  # vertex
        ".frag",  # fragment
        ".geom",  # geometry
        ".tesc",  # tessellation control
        ".tese",  # tessellation evaluation
        ".comp",  # compute
    },
}

_EXT_TO_MOD: dict[str, str] = {}
for _k, _v in _MOD_TO_EXT.items():
    for _ext in _v:
        _EXT_TO_MOD[_ext] = _k

_MODULE_NAMES: list[str] = []
for _d in importlib.metadata.distributions():
    if _d.name.startswith("tree-sitter-"):
        # tree-sitter-{lang} -> tree_sitter_{lang}
        _MODULE_NAMES.append(_d.name.replace("-", "_"))


@lru_cache(maxsize=None)
def _capsule_from_name(lang: str) -> CapsuleType:
    """
    Import a `tree-sitter-<lang>` package and return its `language()` capsule.

    Parameters
    ----------
    lang : str
        Language identifier (e.g. "python", "c").  Case-insensitive.

    Returns
    -------
    CapsuleType
        The PyCapsule returned by the module's `language()`, ready for use with
        :class:`tree_sitter.Language`.

    Raises
    ------
    ValueError
        If *lang* is not a supported tree-sitter package.
    ModuleNotFoundError
        (unlikely after the check) - only if the import fails unexpectedly.
    AttributeError
        When the module does **not** expose `language()` as expected.

    Notes
    -----
    The function remains cached (`lru_cache`) so repeated calls for a language are O(1).
    """
    # Normalise input to lower-case
    lang = lang.lower()

    # Quick sanity check
    module_name = f"tree_sitter_{lang}"
    if module_name not in _MODULE_NAMES:
        raise ValueError(
            f"No tree-sitter package found for language '{lang}'. "
            f"Supported languages are: {', '.join(_MOD_TO_EXT.keys())}"
        )

    # Import the module
    try:
        module = importlib.import_module(module_name)
    except ModuleNotFoundError as exc:  # pragma: no cover
        # This should never happen, but we keep it explicit.
        raise ModuleNotFoundError(f"Failed to load package '{module_name}'.") from exc

    # Verify the API contract
    if not hasattr(module, "language"):
        raise AttributeError(
            f"The module '{module_name}' does not expose a 'language()' function."
        )

    return getattr(module, "language")()


@lru_cache(maxsize=None)
def _capsule_from_path(path: Union[str, Path]) -> CapsuleType:
    """
    Import `path` and return the `language()` capsule.

    Returns: CapsuleType | None
        The PyCapsule that :class:`tree_sitter.Language` expects, or
        `None` if the module cannot be imported or does not expose
        `language()`.

    Raises ValueError if the extension does not exist.
    """
    suffix = Path(path).resolve().suffix.lower()
    lang = _EXT_TO_MOD.get(suffix)
    if not lang:
        raise ValueError(
            f"Unsupported file extension '{suffix}'. "
            f"Supported extensions are: {sorted(_EXT_TO_MOD.keys())}"
        )
    return _capsule_from_name(lang)


class TextSitter:
    """A simple, language agnostic, tree-sitter convenience wrapper."""

    @staticmethod
    def capsule(lang_or_path: Union[str, Path]) -> CapsuleType:
        # note: capsule type is void*
        return (
            _capsule_from_path(lang_or_path)
            if Path(lang_or_path).is_file()
            else _capsule_from_name(lang_or_path)
        )

    @staticmethod
    def language(lang_or_path: Union[str, Path]) -> Language:
        """
        Return a :class:`tree_sitter.Language` instance.

        The function is idempotent: repeated calls for the same language
        reuse the cached `Language` object.
        """
        return Language(TextSitter.capsule(lang_or_path))

    @staticmethod
    def parser(lang_or_path: Union[str, Path]) -> Parser:
        """Return a :class:`tree_sitter.Parser` for a language."""
        return Parser(TextSitter.language(lang_or_path))

    @staticmethod
    def tree(
        lang_or_path: Union[str, Path],
        source: Optional[Union[str, bytes]] = None,
    ) -> Tree:
        parser = TextSitter.parser(lang_or_path)

        # Case 1 – a real file exists → parse it directly
        path = Path(lang_or_path)
        if path.is_file():
            return parser.parse(path.read_bytes())

        # Case 2 – treat *lang_or_path* as the language name.
        if source is None:
            raise ValueError(
                f"Expected `source` when `{lang_or_path}` does not refer to a file."
            )

        data = source.encode() if isinstance(source, str) else bytes(source)
        return parser.parse(data)

    @staticmethod
    def query(lang_or_path: Language, sexpression: str) -> Query:
        """Return a :class:`tree_sitter.Query` for a language."""
        language = TextSitter.language(lang_or_path)
        return Query(language, sexpression)

    @staticmethod
    def captures(query: Query, root: Node) -> dict[str, list[Node]]:
        return QueryCursor(query).captures(root)


# Public API
__all__ = ["TextSitter"]

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

    # Parse source from io
    tree_file = TextSitter.tree(args.path)

    # note: language.version is deprecated. use language.abi_version instead.
    # a warning will be emitted to standard output if version is used.
    print(f"Language Name: {tree_file.language.name}")
    print(f"ABI Version: {tree_file.language.abi_version}")
    print(f"Root Node Type: {tree_file.root_node.type}")
    print(f"Number of children: {tree_file.root_node.child_count}")

    walk(tree_file.root_node)

    # Parse from string (language name + source)
    source_code = """
    import fubar
    from padme import hum

    QUX = "bar"

    class Foo:
        @property
        def bar(self):
            return QUX

    def baz(foo: Foo):
        print(foo.bar)

    def main():
        foo = Foo()
        baz(foo)

    if __name__ == "__main__":
        main()
    """

    # Parse source from str
    tree_source = TextSitter.tree("python", source_code)

    print(f"Language Name: {tree_source.language.name}")
    print(f"ABI Version: {tree_source.language.abi_version}")
    print(f"Root Node Type: {tree_source.root_node.type}")
    print(f"Number of children: {tree_source.root_node.child_count}")

    walk(tree_source.root_node)
