"""
agent.parser.loader
Attempt to guess, load, and return a tree-sitter parser.
"""

import importlib
import importlib.metadata
import importlib.util
import sys
from pathlib import Path
from typing import Optional, Union

from tree_sitter import Language, Parser, Tree

# note: markdown and latex are not supported by tree-sitter

# map extensions to modules
# module names, e.g. tree-sitter-c
MOD_MAP = {
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


def guess_module(path: str) -> Optional[str]:
    return MOD_MAP.get(path.suffix.lower())


def guess_capsule(name: str) -> Optional[Language]:
    if name is None:
        return None  # gracefully handle markdown

    pkg_name = f"tree-sitter-{name}"
    for dist in importlib.metadata.distributions():
        dist_name = dist.metadata["Name"]
        if dist_name != pkg_name:
            continue  # skip

        mod_name = dist_name.replace("-", "_")
        mod_spec = importlib.util.find_spec(mod_name)
        if mod_spec is None:
            return None  # invalid import

        module = importlib.util.module_from_spec(mod_spec)
        sys.modules[mod_name] = module

        # pyright complains about this, but it's assertion is invalid.
        # this is documented in the official python docs.
        # https://docs.python.org/3/library/importlib.html#importing-a-source-file-directly
        # using __import__ directly is considered to be an anti-pattern.
        mod_spec.loader.exec_module(module)  # type: ignore

        # https://docs.python.org/3/c-api/capsule.html
        # https://docs.python.org/3/extending/extending.html#using-capsules
        return module.language()  # returns a PyCapsule object (e.g. void*)


def parse_file(source: Union[str, Path]) -> Optional[Tree]:
    path = Path(source)
    name = guess_module(path)
    capsule = guess_capsule(name)
    if capsule is None:
        return None  # unsupported language

    language = Language(capsule)
    parser = Parser(language)
    return parser.parse(path.read_bytes())


# example usage
if __name__ == "__main__":
    from argparse import ArgumentParser

    parser = ArgumentParser()
    parser.add_argument("path", help="Path to a plain text source file")
    args = parser.parse_args()
    tree = parse_file(args.path)
    print(tree)
    for node in tree.root_node.children:
        print(node)
