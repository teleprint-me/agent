"""
Simple text vs binary file classifier.

Heuristic:
* Empty files → text.
* Any NULL byte (0x00) in the first 512 bytes → binary.
* If >30 % of those bytes are outside the printable ASCII range + common whitespace,
  we consider it binary; otherwise, text.
"""

from pathlib import Path


def is_ascii_bytes(data: bytes, threshold: float = 0.30) -> bool:
    """
    Return True if at least `threshold` of *data* is printable ASCII or common whitespace.
    ref: https://stackoverflow.com/a/1446870
    """
    # Add control char set
    control = {b"\n"[0], b"\r"[0], b"\t"[0], b"\b"[0]}
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


def is_text_file(path: Path) -> bool:
    """
    Read the first 512 bytes of *path* and classify it.
    Return True if `data` looks like plain ASCII/UTF-8 text.
    """

    with open(path, "rb") as file:
        data = file.read(512)

        # Empty file, text by definition
        if not data:
            return True

        # Binary files almost always contain NULL
        if 0 in data:
            return False

        if is_ascii_bytes(data):
            return True

    try:
        return bool(data.decode())
    except UnicodeDecodeError:
        return False


if __name__ == "__main__":
    from argparse import ArgumentParser

    parser = ArgumentParser()
    parser.add_argument("path", help="Input file to classify.")
    args = parser.parse_args()

    print(f"Is text file: {is_text_file(args.path)}")
