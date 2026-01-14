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

import multiprocessing
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Iterable, Optional, Union

# some kind of black magic going on with str == bytes
from magic import Magic

# --- Supported classes ---

# there has to be a better way than this 🫠
EXT_TO_CLS = {
    ".txt": "text",
    ".c": "c",
    ".h": "c",
    ".cpp": "cpp",
    ".hpp": "cpp",
    ".rs": "rust",
    ".py": "python",
    ".pyi": "python",
    ".sh": "bash",
    ".md": "markdown",
    ".htm": "html",
    ".html": "html",
    ".css": "css",
    ".json": "json",
    ".js": "javascript",
    ".mjs": "javascript",
    ".pdf": "postscript",  # not really a class but ok for now
    ".png": "image",
    ".jpg": "image",
    ".jpeg": "image",
}


def supported_suffixes() -> set[str]:
    return set(EXT_TO_CLS.keys())


# will need this later
def supported_classes() -> set[str]:
    return set(EXT_TO_CLS.values())


def supported_candidates(path: Union[str, Path]) -> Iterable[Path]:
    """Yield only files whose suffix is in EXT_TO_CLS."""
    for p in Path(path).rglob("*"):
        if p.is_file() and p.suffix.lower() in supported_suffixes():
            yield p


# --- Text classification ---


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
        return False  # NUL byte → binary
    return is_ascii(data, threshold) or is_unicode(data)


# --- Mime classification ---


def magic_mime_type(path: Union[str, Path]) -> Optional[str]:
    return Magic(mime=True).from_file(Path(path)) or None


def magic_mime_encoding(path: Union[str, Path]) -> Optional[str]:
    return Magic(mime_encoding=True).from_file(Path(path)) or None


def magic_mime_class(path: Union[str, Path]) -> Optional[str]:
    # our own extension → class mapping
    return EXT_TO_CLS.get(Path(path).suffix.lower(), None)


def magic_mime_file(path: Union[str, Path]) -> dict[str, Optional[str]]:
    return {
        "class": magic_mime_class(path),
        "type": magic_mime_type(path),
        "encoding": magic_mime_encoding(path),
    }


# --- File classification ---


def classify(path: Union[str, Path], threshold: float = 0.30) -> dict[str, any]:
    """Return a serialisable dictionary describing *path*."""
    p = Path(path).resolve()
    data = p.read_bytes()[:512]  # 512‑byte sample
    meta = magic_mime_file(p)

    return {
        "text": is_text(data, threshold),
        "path": str(p),
        "parent": str(p.parent),
        "stem": p.stem,
        "size": p.stat().st_size,
        "suffix": p.suffix or None,
        **meta,  # libmagic output (may be None)
    }


# --- File collection ---


def collect(
    path: Union[str, Path],
    max_workers: int = 4,
    timeout: float = 30.0,
) -> list[dict[str, any]]:
    """
    Recursively walk *path* (file or directory), classify each supported file,
    and return a **list** of serialisable dictionaries.

    Parameters
    ----------
    path : Union[str, pathlib.Path]
        Target to scan.
    max_workers : int
        Number of threads when *parallel* is true (default: 4).
    timeout : float
        The maximum number of seconds to wait (default: 30.0).
    """
    p = Path(path)

    if p.is_file():
        return [classify(p)]

    if max_workers <= 0:
        max_workers = multiprocessing.cpu_count()

    # Collect all supported files first;
    # this avoids the overhead of submitting a task per file in a loop.
    candidates = list(supported_candidates(p))
    results: list[dict[str, any]] = []
    with ThreadPoolExecutor(max_workers=max_workers) as exe:
        future_to_path = {exe.submit(classify, fp): fp for fp in candidates}
        for fut in as_completed(future_to_path, timeout=timeout):
            try:
                results.append(fut.result())
            except Exception as exc:  # pragma: no cover
                logging.warning("Failed to classify %s: %s", future_to_path[fut], exc)

    return results


if __name__ == "__main__":
    import json
    from argparse import ArgumentParser

    parser = ArgumentParser(description="Classify files by type & text-ability.")
    parser.add_argument(
        "path",
        help="File or directory to scan.",
    )
    parser.add_argument(
        "--max-workers",
        type=int,
        default=4,
        help="Number of cpu cores to utilize (default: 4).",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=30.0,
        help="The maximum number of seconds to wait (default: 30.0).",
    )
    args = parser.parse_args()

    for cls in collect(args.path, args.max_workers, args.timeout):
        print(f"class: {json.dumps(cls, indent=2)}")
