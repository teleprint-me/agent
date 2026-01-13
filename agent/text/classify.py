"""
Simple text vs binary file classifier.

Heuristic:
* Empty files → text.
* Any NULL byte (0x00) in the first 512 bytes → binary.
* If >30 % of those bytes are outside the printable ASCII range + common whitespace,
  we consider it binary; otherwise, text.

Reference: https://stackoverflow.com/a/1446870/15147156
"""

from pathlib import Path

# some kind of black magic going on with str == bytes
from magic import detect_from_filename

# there has to be a better way than this 🫠
EXT_TO_CLS = {
    ".txt": "text",
    ".c": "c",
    ".h": "c",
    ".cpp": "cpp",
    ".hpp": "cpp",
    ".rs": "rust",
    ".py": "python",
    ".sh": "bash",
    ".md": "markdown",
    ".htm": "html",
    ".html": "html",
    ".css": "css",
    ".json": "json",
    ".js": "javascript",
    ".mjs": "javascript",
    ".pdf": "postscript",
    ".png": "image",
    ".jpg": "image",
    ".jpeg": "image",
}


def is_ascii(data: bytes, threshold: float = 0.30) -> bool:
    """
    Return True if `data` looks like ASCII.
    """

    if not data:
        return True

    # Add control char set
    control: int = {
        ord("\n"),  # line feed
        ord("\r"),  # carriage return
        ord("\t"),  # tab
        ord("\b"),  # backspace
    }

    # Add printable char set
    characters = set(range(0x20, 0x7F))
    # Build a set containing every element from either operand
    allowed = characters | control
    # Compute number of raw bytes
    byte_count = sum(1 for b in data if b not in allowed)
    # Compute ratio between raw bytes and data
    byte_ratio = byte_count / len(data)
    # If more than x % non-text characters, classify as a binary
    return byte_ratio < threshold


def is_unicode(data: bytes) -> bool:
    """Return True if `data` looks like UTF-8."""
    if not data:
        return True

    try:
        return bool(data.decode("utf-8"))
    except UnicodeDecodeError:
        return False


def is_text(data: bytes, threshold: float = 0.30) -> bool:
    """Return True if `data` looks like ASCII/UTF-8 text."""

    # Empty file, text by definition
    if not data:
        return True

    # Binary files almost always contain NULL
    if 0 in data:
        return False

    # Plain text is ASCII
    if is_ascii(data, threshold):
        return True

    # Binary files can not be decoded
    if is_unicode(data):
        return True

    return False


def magic(path: Path) -> dict[str, any]:
    path = Path(path).resolve()
    magic = detect_from_filename(path)
    data = path.read_bytes()[:512]

    # this should be serializable (se-​ri-​al-​iza-ble 🧐)
    return {
        "text": is_text(data),
        "path": str(path),
        "parent": str(path.parent),
        "stem": path.stem,
        "size": path.stat().st_size,
        "suffix": path.suffix or None,
        "class": EXT_TO_CLS.get(path.suffix, None),
        "mime_type": getattr(magic, "mime_type", None),
        "encoding": getattr(magic, "encoding", None),
    }


def collect(path: Path):
    path = Path(path)

    if path.is_file():
        return [magic(path)]

    collection = []
    for dirname, _, filenames in os.walk(args.path):
        for name in filenames:
            filepath = Path(f"{dirname}/{name}")
            collection.append(magic(filepath))
    return collection


if __name__ == "__main__":
    import json
    import os
    from argparse import ArgumentParser

    parser = ArgumentParser()
    parser.add_argument("path", help="Input file to classify.")
    args = parser.parse_args()

    for cls in collect(args.path):
        print(f"class: {json.dumps(cls, indent=2)}")
