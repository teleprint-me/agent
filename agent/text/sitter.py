# agent/text/sitter.py
"""
Copyright (C) 2023 Austin Berrio

Utilities for loading Tree-Sitter languages, parsers, trees, queries, and captures.

The module is intentionally lightweight - each helper caches immutable
`tree_sitter.Language` objects via `functools.lru_cache` so repeated look-ups
are O(1).  The public API is a single `TextSitter` class that exposes
language-agnostic helpers as staticmethods.

Typical usage:

>>> from agent.text.sitter import TextSitter
>>> tree = TextSitter.tree("python", "print('hello')")
>>> tree.root_node.type
'module'
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

# Note: LaTeX is not supported by tree-sitter.
# there has to be a better way than this 🫠

# Map module names to file extensions
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

# Map file extensions to module names
_EXT_TO_MOD: dict[str, str] = {}
for _k, _v in _MOD_TO_EXT.items():
    for _ext in _v:
        _EXT_TO_MOD[_ext] = _k

# Discover installed tree-sitter packages
_MODULE_NAMES: list[str] = []
for _d in importlib.metadata.distributions():
    if _d.name.startswith("tree-sitter-"):
        # tree-sitter-{lang} -> tree_sitter_{lang}
        _MODULE_NAMES.append(_d.name.replace("-", "_"))


# --------------------------------------------------------------------------- #
# Helper functions - cached
# --------------------------------------------------------------------------- #
@lru_cache(maxsize=None)
def _capsule_from_name(lang: str) -> CapsuleType:
    """
    Return the PyCapsule for *lang* by importing the corresponding
    `tree_sitter_<lang>` module.

    Parameters
    ----------
    lang : str
        Language identifier (case-insensitive).
        Example: `"python"` or `"c"`.

    Returns
    -------
    CapsuleType
        The value returned by the module's `language()` function.
        Example: A `void *` that `tree_sitter.Language` can consume.

    Raises
    ------
    ValueError
        If *lang* does not map to a known `tree-sitter-` distribution.
    ModuleNotFoundError
        If the import of the module fails.
        Note: This should never happen after the `_MODULE_NAMES` check.
    AttributeError
        If the module does not expose a `language()` attribute.
    """
    lang = lang.lower()
    module_name = f"tree_sitter_{lang}"
    if module_name not in _MODULE_NAMES:
        raise ValueError(
            f"No tree-sitter package found for language '{lang}'. "
            f"Supported languages are: {', '.join(_MOD_TO_EXT.keys())}"
        )

    try:
        module = importlib.import_module(module_name)
    except ModuleNotFoundError as exc:  # pragma: no cover
        raise ModuleNotFoundError(f"Failed to load package '{module_name}'.") from exc

    if not hasattr(module, "language"):
        raise AttributeError(
            f"The module '{module_name}' does not expose a 'language()' function."
        )

    return getattr(module, "language")()


@lru_cache(maxsize=None)
def _capsule_from_path(path: Union[str, Path]) -> CapsuleType:
    """
    Resolve a file extension to a language capsule.

    Parameters
    ----------
    path : Union[str, Path]
        Path to a source file.  The file must exist and its suffix must be
        recognised by `_EXT_TO_MOD`.

    Returns
    -------
    CapsuleType
        The capsule returned by the appropriate `tree_sitter_<lang>` module.

    Raises
    ------
    ValueError
        If the file suffix is unknown.
    """
    suffix = Path(path).resolve().suffix.lower()
    lang = _EXT_TO_MOD.get(suffix)
    if not lang:
        raise ValueError(
            f"Unsupported file extension '{suffix}'. "
            f"Supported extensions are: {sorted(_EXT_TO_MOD.keys())}"
        )
    return _capsule_from_name(lang)


# Public API
class TextSitter:
    """
    A tiny, language-agnostic wrapper around the `tree_sitter` API.

    Every helper is a :py:func:`staticmethod` that lazily loads the
    corresponding `Language` object - the object is cached via
    `functools.lru_cache` for O(1) repeated access.  The design keeps the
    public surface minimal while still exposing all common patterns:

    * `capsule` - returns the raw `void *` capsule.
    * `language` - a :class:`tree_sitter.Language` instance.
    * `parser` - a :class:`tree_sitter.Parser`.
    * `tree` - a :class:`tree_sitter.Tree` parsed from a file or a string.
    * `query` - a :class:`tree_sitter.Query` for a language.
    * `captures` - helper to run a `QueryCursor` over a subtree.
    """

    @staticmethod
    def capsule(lang_or_path: Union[str, Path]) -> CapsuleType:
        """
        Return the underlying PyCapsule for *lang_or_path*.

        Parameters
        ----------
        lang_or_path : Union[str, Path]
            Either a language identifier (e.g. `"python"`) or a path to a
            source file.  If a file exists, the method resolves the suffix
            to a language; otherwise it treats the argument as a language
            name.

        Returns
        -------
        CapsuleType
            The `void *` returned by the `tree_sitter_<lang>.language()`.
        """
        return (
            _capsule_from_path(lang_or_path)
            if Path(lang_or_path).is_file()
            else _capsule_from_name(lang_or_path)
        )

    @staticmethod
    def language(lang_or_path: Union[str, Path]) -> Language:
        """
        Return a cached :class:`tree_sitter.Language` for *lang_or_path*.

        Parameters
        ----------
        lang_or_path : Union[str, Path]
            Language name or path to a source file.

        Returns
        -------
        tree_sitter.Language
            A language instance ready to be fed into a `Parser`.
        """
        return Language(TextSitter.capsule(lang_or_path))

    @staticmethod
    def parser(lang_or_path: Union[str, Path]) -> Parser:
        """
        Return a :class:`tree_sitter.Parser` for *lang_or_path*.

        Parameters
        ----------
        lang_or_path : Union[str, Path]
            Language name or path to a source file.

        Returns
        -------
        tree_sitter.Parser
            A new parser instance bound to the requested language.
        """
        return Parser(TextSitter.language(lang_or_path))

    @staticmethod
    def tree(
        lang_or_path: Union[str, Path],
        source: Optional[Union[str, bytes]] = None,
    ) -> Tree:
        """
        Parse *source* or a file into a :class:`tree_sitter.Tree`.

        Parameters
        ----------
        lang_or_path : Union[str, Path]
            Language name or path to a source file.
        source : Optional[Union[str, bytes]]
            Source code to parse when `lang_or_path` does **not** point
            to an existing file.  Must be supplied in that case.

        Returns
        -------
        tree_sitter.Tree
            The parse tree.  The returned `Tree` has the `language`
            attribute pointing to the underlying `Language` instance.

        Raises
        ------
        ValueError
            If `source` is omitted when `lang_or_path` does not refer to
            an existing file.
        """
        parser = TextSitter.parser(lang_or_path)

        path = Path(lang_or_path)
        if path.is_file():
            return parser.parse(path.read_bytes())

        if source is None:
            raise ValueError(
                f"Expected `source` when `{lang_or_path}` does not refer to a file."
            )

        data = source.encode() if isinstance(source, str) else bytes(source)
        return parser.parse(data)

    @staticmethod
    def query(lang_or_path: Union[str, Path], sexpression: str) -> Query:
        """
        Compile a tree-sitter query for *lang_or_path*.

        Parameters
        ----------
        lang_or_path : Union[str, Path]
            Language name or path to a source file.
        sexpression : str
            The S-expression string describing the query.

        Returns
        -------
        tree_sitter.Query
            A compiled query ready to be executed with a :class:`QueryCursor`.

        Raises
        ------
        tree_sitter.tree_sitter_error.TreeSitterError
            If the query string is invalid for the chosen language.
        """
        language = TextSitter.language(lang_or_path)
        return Query(language, sexpression)

    @staticmethod
    def captures(query: Query, root: Node) -> dict[str, list[Node]]:
        """
        Execute *query* on *root* and return the capture mapping.

        Parameters
        ----------
        query : tree_sitter.Query
            Compiled query to run.
        root : tree_sitter.Node
            The node (typically a `Tree.root_node`) to run the query on.

        Returns
        -------
        dict[str, list[tree_sitter.Node]]
            Mapping from capture names to the list of nodes that matched.
        """
        return QueryCursor(query).captures(root)

    @staticmethod
    def walk(root: Node) -> Iterable[Node]:
        """
        Depth-first traversal that yields each node exactly once.

        Parameters
        ----------
        root : tree_sitter.Node
            Starting node of the traversal.

        Yields
        ------
        tree_sitter.Node
            Each node in the subtree rooted at *root*.
        """
        stack: list[Node] = [root]
        while stack:
            node = stack.pop()
            yield node
            # children are already in left-to-right order
            stack.extend(reversed(node.children))

    @staticmethod
    def collect(
        root: Node,
        keep_types: Optional[Set[str]] = None,
    ) -> Iterable[Node]:
        """
        Yield nodes that match *keep_types* (or all leaf nodes if `None`).

        Parameters
        ----------
        root : tree_sitter.Node
            Root of the subtree to walk.
        keep_types : Optional[Set[str]]
            Node types to keep.  If `None` the traversal stops at leafs.

        Yields
        ------
        tree_sitter.Node
            Matching nodes in depth-first order.
        """
        for node in TextSitter.walk(root):
            if keep_types is None:
                # leaf-only - node has no children
                if not node.children:
                    yield node
            else:
                if node.type in keep_types:
                    yield node

    @staticmethod
    def pretty_print(root: Node, depth: int = 0, margin: int = 30) -> None:
        """
        Pretty-print a small subtree to `stdout`.

        Parameters
        ----------
        root : tree_sitter.Node
            Node to render.
        depth : int, default 0
            Current depth - used only for indentation.
        margin : int, default 30
            Truncate node text to this many bytes before decoding.
        """
        indent = "  " * depth
        txt = root.text[:margin].decode("utf8", errors="replace")
        print(f"{indent}{root.type:2} ({txt!r})")
        for child in root.children:
            TextSitter.pretty_print(child, depth + 1, margin)


# Public API
__all__ = ["TextSitter"]

# Demo / doctest
if __name__ == "__main__":  # pragma: no cover
    from argparse import ArgumentParser, Namespace

    def parse_args() -> Namespace:
        parser = ArgumentParser(description="Parse a source file with tree-sitter.")
        parser.add_argument("path", help="Path to a plain text source file")
        return parser.parse_args()

    args = parse_args()

    # Parse source from io
    tree_file = TextSitter.tree(args.path)

    # note: language.version is deprecated. use language.abi_version instead.
    # a warning will be emitted to standard output if version is used.
    print(f"Language Name: {tree_file.language.name}")
    print(f"ABI Version: {tree_file.language.abi_version}")
    print(f"Root Node Type: {tree_file.root_node.type}")
    print(f"Number of children: {tree_file.root_node.child_count}")

    TextSitter.pretty_print(tree_file.root_node)

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

    TextSitter.pretty_print(tree_source.root_node)
