"""
agent.parser.loader
Attempt to guess, load, and return a tree-sitter parser.
"""

import importlib
import importlib.metadata
import os
import sys
from importlib.machinery import ModuleSpec
from pathlib import Path
from typing import Iterable, Optional

import magic
from tree_sitter import Language, Parser, Tree

# note: markdown is not supported by tree-sitter

# module names, e.g. tree-sitter-c
c = "c"
cpp = "cpp"
rust = "rust"
bash = "bash"
python = "python"
html = "html"
css = "css"
javascript = "javascript"

# map extensions to module
MOD_MAP = {
    ".c": c,
    ".h": c,
    ".cpp": cpp,
    ".hpp": cpp,
    ".rs": rust,
    ".py": python,
    ".sh": bash,
    ".html": html,
    ".css": css,
    ".js": javascript,
}


def guess_module(source: str) -> Optional[str]:
    path = Path(source).suffix.lower()
    return MOD_MAP.get(path)


def guess_language(source: str) -> Optional[Language]:
    mod_type = guess_module(source)
    if mod_type is None:
        return None  # gracefully handle markdown

    pkg_name = f"tree-sitter-{mod_type}"
    for dist in importlib.metadata.distributions():
        dist_name = dist.metadata["Name"]
        if dist_name != pkg_name:
            continue
        mod_name = dist_name.replace("-", "_")
        mod_spec = importlib.util.find_spec(mod_name)
        if mod_spec is None:
            return None  # invalid import
        module = importlib.util.module_from_spec(mod_spec)
        sys.modules[mod_name] = module
        spec.loader.exec_module(module)
        return module.language()


def parse_file(source: str) -> Optional[Tree]:
    path = Path(source)
    data = path.read_bytes()
    capsule = guess_language(source)
    if capsule is None:
        return None
    language = Language(capsule)
    parser = Parser(language)
    return parser.parse(data)
