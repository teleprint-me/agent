"""
https://pythonassets.com/posts/treeview-in-tk-tkinter
"""

import os
import tkinter as tk
from pathlib import Path

import ttkbootstrap as ttk
from ttkbootstrap.constants import *

EXCLUDED_DIRS = {"__pycache__", "build", ".git", ".venv", ".mypy_cache"}
EXCLUDED_FILES = {".flake8", ".gitignore"}


def get_full_path(tree, node_id):
    parts = []
    while node_id:
        parts.insert(0, tree.item(node_id)["text"])
        node_id = tree.parent(node_id)
    path = os.path.join(Path(os.getcwd()).parent, *parts)
    return path


def list_directory(tree, parent, path):
    try:
        for entry in sorted(os.listdir(path)):
            full_path = os.path.join(path, entry)

            if entry.startswith(".") or entry in EXCLUDED_FILES:
                continue
            if os.path.isdir(full_path) and entry in EXCLUDED_DIRS:
                continue

            node_id = tree.insert(parent, "end", text=entry, open=False)

            if os.path.isdir(full_path):
                # Add a dummy child to make it expandable
                tree.insert(node_id, "end", text="")

    except PermissionError:
        pass  # Skip dirs we can't access


def on_open_node(event):
    tree = event.widget
    node_id = tree.focus()
    path = get_full_path(tree, node_id)
    # Only populate if not already expanded
    if tree.get_children(node_id):
        first_child = tree.get_children(node_id)[0]
        if not tree.get_children(first_child):  # only expand once
            tree.delete(first_child)
            list_directory(tree, node_id, path)


def main():
    root = ttk.Window(title="Repo Tree", themename="darkly")
    root.geometry("500x400")

    tree = ttk.Treeview(root)
    tree.pack(fill="both", expand=True)

    base_path = os.getcwd()
    base_name = os.path.basename(base_path)
    root_node = tree.insert("", "end", text=base_name, values=[base_path], open=True)

    list_directory(tree, root_node, base_path)

    tree.bind("<<TreeviewOpen>>", on_open_node)

    root.mainloop()


if __name__ == "__main__":
    main()
