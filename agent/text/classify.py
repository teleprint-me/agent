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

from magic import detect_from_filename


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


def classify(path: Path) -> dict[str, any]:
    path = Path(path).resolve()
    magic = detect_from_filename(path)
    data = path.read_bytes()[:512]

    return {
        "text": is_text(data),
        "path": str(path),
        "parent": str(path.parent),
        "stem": path.stem,
        "size": path.stat().st_size,
        "suffix": getattr(path, "suffix", None),
        "mime_type": getattr(magic, "mime_type", None),
        "encoding": getattr(magic, "encoding", None),
    }


if __name__ == "__main__":
    import json
    from argparse import ArgumentParser

    parser = ArgumentParser()
    parser.add_argument("path", help="Input file to classify.")
    args = parser.parse_args()

    print(f"Class: {json.dumps(classify(args.path), indent=2)}")
