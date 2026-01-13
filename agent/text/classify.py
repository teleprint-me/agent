"""
Simple text vs binary file classifier.

Heuristic:
* Empty files → text.
* Any NULL byte (0x00) in the first 512 bytes → binary.
* If >30 % of those bytes are outside the printable ASCII range + common whitespace,
  we consider it binary; otherwise, text.

References:
  - Detecting Plain Text Files:
    https://stackoverflow.com/a/1446870/15147156
  - IANA Media Types:
    https://www.iana.org/assignments/media-types/media-types.xhtml
"""

import os
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


# --- Helpers – pure functions, easy to unit‑test ---


def is_ascii(data: bytes, threshold: float = 0.30) -> bool:
    """Return True if `data` looks like ASCII."""

    if not data:
        return True
    control_chars = {ord("\n"), ord("\r"), ord("\t"), ord("\b")}
    printable = set(range(0x20, 0x7F))
    allowed = printable | control_chars
    non_text = sum(b not in allowed for b in data)
    return (non_text / len(data)) < threshold


def is_unicode(data: bytes) -> bool:
    """Return True if `data` looks like UTF-8."""

    if not data:
        return True
    try:
        data.decode("utf-8")
        return True
    except UnicodeDecodeError:
        return False


def is_text(data: bytes, threshold: float = 0.30) -> bool:
    """Return `True` for ASCII or UTF-8 text, otherwise `False`."""

    if not data:
        return True  # empty file → "text"
    if 0 in data:
        return False  # NUL byte => binary
    return is_ascii(data, threshold) or is_unicode(data)


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
    for dirname, _, filenames in os.walk(path):
        for name in filenames:
            filepath = Path(f"{dirname}/{name}")
            cls = EXT_TO_CLS.get(filepath.suffix, None)
            if cls is None:
                print(f"Warn: {filepath.suffix} is unsupported")
                continue  # skip unsupported files
            collection.append(magic(filepath))
    return collection


if __name__ == "__main__":
    import json
    from argparse import ArgumentParser

    parser = ArgumentParser()
    parser.add_argument("path", help="Input file to classify.")
    args = parser.parse_args()

    for cls in collect(args.path):
        print(f"class: {json.dumps(cls, indent=2)}")
