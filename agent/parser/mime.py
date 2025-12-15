"""
agent.parser.mime
Get the mime type of a given file object.
"""

import inspect
from argparse import ArgumentParser
import os
from pathlib import Path
import magic
from typing import Iterator


# note that FileMagic has no internal __dict__.
# use dir instead of vars
# has 3 primary properties:
#   - encoding, e.g. utf-8
#   - mime_type, e.g. text/plain
#   - name, e.g. Unicode text, UTF-8 text
def log_magic(path: Path):
    file_magic = magic.detect_from_filename(path)

    print(f"Path: {path}")
    print(f"FileMagic.encoding = '{file_magic.encoding}'")
    print(f"FileMagic.mime_type = '{file_magic.mime_type}'")
    print(f"FileMagic.name = '{file_magic.name}'")


def walk_path(root: Path) -> Iterator[Path]:
    for entry in os.scandir(root):
        # ignore hidden paths
        if entry.name.startswith("."):
            continue

        if entry.is_dir():
            yield from walk_path(Path(entry.path))
            continue

        if entry.is_file():
            yield Path(entry.path)


parser = ArgumentParser("python -m agent.parser.mime", description="Guess the mime type of a file")
parser.add_argument("path", help="Path to a file or directory")
args = parser.parse_args()

path = Path(args.path)
if path.is_file():
    log_magic(path)
    exit(0)

if not path.is_dir():
    raise ValueError("Path must be a file or directory")

for entry in walk_path(path):
    log_magic(entry)
    print()  # pad with newline
