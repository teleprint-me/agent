# agent/text/sitter.py
"""
Copyright (C) 2023 Austin Berrio

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
        Language identifier (e.g. "python", "c").  Case‑insensitive.

    Returns
    -------
    CapsuleType
        The PyCapsule returned by the module’s `language()`, ready for use with
        :class:`tree_sitter.Language`.

    Raises
    ------
    ValueError
        If *lang* is not a supported tree‑sitter package.
    ModuleNotFoundError
        (unlikely after the check) – only if the import fails unexpectedly.
    AttributeError
        When the module does **not** expose `language()` as expected.

    Notes
    -----
    The function remains cached (`lru_cache`) so repeated calls for a language are O(1).
    """
    # Normalise input to lower‑case
    lang = lang.lower()

    # Quick sanity check
    module_name = f"tree_sitter_{lang}"
    if module_name not in _MODULE_NAMES:
        raise ValueError(
            f"No tree‑sitter package found for language '{lang}'. "
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


def get_language(lang_or_path: Union[str, Path]) -> Language:
    """
    Return a :class:`tree_sitter.Language` instance.

    The function is idempotent: repeated calls for the same language
    reuse the cached `Language` object.
    """
    if Path(lang_or_path).is_file():
        capsule = _capsule_from_path(lang_or_path)
        return Language(capsule)
    capsule = _capsule_from_name(lang_or_path)
    return Language(capsule)  # note: capsule type is void*


def get_parser(lang_or_path: Union[str, Path]) -> Parser:
    """
    Create a fresh :class:`tree_sitter.Parser` for a language.

    A new `Parser` instance is returned each time - this is intentional
    because parsers hold mutable state that is useful when editing a file
    incrementally.
    """
    language = get_language(lang_or_path)
    return Parser(language)


def get_tree(
    lang_or_path: Union[str, Path],
    source: Optional[Union[str, bytes]] = None,
) -> Tree:
    """
    Parse a source file or string with tree‑sitter.

    Parameters
    ----------
    lang_or_path : str | pathlib.Path
        * If it points at an existing regular file → that file is parsed.
        * Otherwise interpreted as the language identifier (e.g. `"python"`,
          `"c"`, …).  In this mode a source string must be supplied via
          **source**.

    source : str | bytes, optional
        Raw source code to parse when *lang_or_path* is not an existing file.
        When given as text it will be UTF‑8 encoded automatically.  If the
        caller already has a byte‑string just pass that; no double‑encoding
        occurs.

    Returns
    -------
    tree_sitter.Tree

    Raises
    ------
    ValueError
        * `source` is missing while `lang_or_path` does not point at an existing file.
        * The language for the supplied source cannot be found (handled in
          :func:`_capsule_from_name` / :func:`get_parser`).

    Notes
    -----
    This function remains fast because both :func:`get_language` and
    :func:`get_parser` are cached via `lru_cache`.
    """
    path = Path(lang_or_path)

    # Case 1 – a real file exists → parse it directly
    if path.is_file():
        parser = get_parser(path)
        return parser.parse(path.read_bytes())

    # Case 2 – treat *lang_or_path* as the language name.
    # We deliberately raise if no source was supplied; that keeps debugging
    # simple and matches a “crash‑fast” philosophy.
    if source is None:
        raise ValueError(
            f"Expected `source` when `{lang_or_path}` does not refer to a file."
        )

    # Convert the source into raw bytes (UTF‑8 for str, identity for bytes)
    data = source.encode() if isinstance(source, str) else bytes(source)

    parser = get_parser(lang_or_path)
    return parser.parse(data)


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

    # Parse a real file
    tree_file = get_tree(args.path)

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
    tree_source = get_tree("python", source=source_code)

    print(f"Language Name: {tree_source.language.name}")
    print(f"ABI Version: {tree_source.language.abi_version}")
    print(f"Root Node Type: {tree_source.root_node.type}")
    print(f"Number of children: {tree_source.root_node.child_count}")

    walk(tree_source.root_node)
