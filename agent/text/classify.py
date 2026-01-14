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

from concurrent.futures import ThreadPoolExecutor, as_completed
from functools import cached_property
from multiprocessing import cpu_count
from pathlib import Path
from types import MappingProxyType
from typing import Final, Iterable, Optional, Union

# some kind of black magic going on with str == bytes
from magic import Magic

_EXT_TO_CLS: dict[str, str] = {
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
    ".pdf": "application",
    ".png": "image",
    ".jpg": "image",
    ".jpeg": "image",
}

# expose a *read‑only* view of the mapping
_MAPPING: MappingProxyType[str, str] = MappingProxyType(_EXT_TO_CLS)
_INVERSE: dict[str, str] = {cls: ext for ext, cls in _MAPPING.items()}
_SUFFIXES: frozenset[str] = frozenset(_EXT_TO_CLS)
_CLASSES: frozenset[str] = frozenset(_EXT_TO_CLS.values())


class TextExtension:
    """Read-only mapping from file extensions to semantic class names."""

    @property
    def mapping(self) -> dict[str, str]:
        """Return a mapping of file extensions to class names."""
        return _MAPPING

    @property
    def inverse(self) -> dict[str, str]:
        """Return a inverted mapping of class names to file extensions."""
        return _INVERSE

    @property
    def suffixes(self) -> set[str]:
        """All known file extension keys (with the leading dot)."""
        return _SUFFIXES

    @property
    def classes(self) -> set[str]:
        """All semantic class names that appear in the mapping."""
        return _CLASSES

    def name(self, suffix: str) -> Optional[str]:
        """Return the mapped class name from a file suffix."""
        return _MAPPING.get(suffix, None)

    def path(self, name: Union[str, Path]) -> Optional[str]:
        """Return the mapped class name from a file path."""
        suffix = Path(name).suffix.lower()
        return self.name(suffix)

    def candidates(self, name: Union[str, Path]) -> Iterable[Path]:
        """Yield file names that have known extensions."""
        for p in Path(name).rglob("*"):
            if p.is_file() and p.suffix.lower() in _MAPPING:
                yield p


class TextDetector:
    def __init__(self, threshold: float = 0.30):
        self.threshold = threshold

    def is_ascii(self, data: bytes) -> bool:
        """Return True if `data` looks like ASCII."""

        if not data:
            return True
        control_chars = {ord("\n"), ord("\r"), ord("\t"), ord("\b")}
        printable = set(range(0x20, 0x7F))
        allowed = printable | control_chars
        non_text = sum(b not in allowed for b in data)
        return (non_text / len(data)) < self.threshold

    def is_unicode(self, data: bytes) -> bool:
        """Return True if `data` looks like UTF-8."""

        if not data:
            return True
        try:
            data.decode("utf-8")
            return True
        except UnicodeDecodeError:
            return False

    def is_text(self, data: bytes) -> bool:
        """Return `True` for ASCII or UTF-8 text, otherwise `False`."""

        if not data:
            return True  # empty file → "text"
        if 0 in data:
            return False  # NUL byte → binary
        return self.is_ascii(data) or self.is_unicode(data)

    def is_binary(self, data: bytes) -> bool:
        return not self.is_text(data)


class TextMagic:
    """Wrap libmagic; return dict(type, encoding, class)."""

    def __init__(self, ext: Optional[TextExtension] = None):
        self._magic = Magic(mime=True, mime_encoding=True)
        self._extension = ext if ext else TextExtension()

    def from_file(self, name: Union[str, Path]) -> dict[str, Optional[str]]:
        """
        Returns (mime_type, encoding).  `encoding` is a charset string,
        e.g. 'utf-8', or None if libmagic couldn't detect it.
        """

        # result: str = "text/plain; charset=utf-8"
        result = self._magic.from_file(name)

        # parse out the metadata
        _type, _enc = result.split(";")

        # get the mime type
        mime_type = None
        if _type:
            mime_type = _type.strip().lower()

        # get the mime encoding
        mime_enc = None
        if _enc:
            mime_enc = _enc.split("=")[-1].strip().lower()

        # get the classifier to validate mime-types
        mime_cls = self._extension.path(name)

        # return the results as a tuple
        return {
            "type": mime_type,
            "encoding": mime_enc,
            "class": mime_cls,
        }


class TextCrawler:
    def __init__(
        self,
        extension: Optional[TextExtension] = None,
        threshold: float = 0.30,
        max_workers: int = 4,
        timeout: float = 30.0,
    ):
        self.extension = extension if extension else TextExtension()
        self.magic = TextMagic(self.extension)
        self.detector = TextDetector(threshold)
        self.max_workers = max_workers if max_workers > 0 else cpu_count()
        self.timeout = timeout

    def classify(self, name: Union[str, Path]) -> dict[str, any]:
        """Return a serialisable dictionary describing the path name."""
        p = Path(name).resolve()
        data = p.read_bytes()[:512]  # 512‑byte sample
        is_text = self.detector.is_text(data)
        meta = self.magic.from_file(p)

        return {
            "path": str(p),
            "parent": str(p.parent),
            "stem": p.stem,
            "size": p.stat().st_size,
            "suffix": p.suffix or None,
            "text": is_text,
            **meta,  # libmagic output (may be None)
        }

    def collect(self, path: Union[str, Path]) -> list[dict[str, any]]:
        """
        Recursively walk *path* (file or directory), classify each supported file,
        and return a **list** of serialisable dictionaries.
        """
        p = Path(path)

        if p.is_file():
            return [self.classify(p)]

        # Collect all supported files first;
        # this avoids the overhead of submitting a task per file in a loop.
        candidates = list(self.extension.candidates(p))
        results: list[dict[str, any]] = []
        with ThreadPoolExecutor(max_workers=self.max_workers) as exe:
            future_to_path = {exe.submit(self.classify, fp): fp for fp in candidates}
            for fut in as_completed(future_to_path, timeout=self.timeout):
                results.append(fut.result())
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

    crawler = TextCrawler(max_workers=args.max_workers, timeout=args.timeout)
    for cls in crawler.collect(args.path):
        print(f"class: {json.dumps(cls, indent=2)}")
