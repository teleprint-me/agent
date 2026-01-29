# agent/text/pdf.py
"""
Copyright (C) 2023 Austin Berrio

A Python script for converting PDF files to plaintext.
- https://en.wikipedia.org/wiki/PDF
- https://pdfminersix.readthedocs.io/en/latest/
"""

import os
from dataclasses import dataclass
from io import StringIO
from pathlib import Path
from typing import List, Union


@dataclass(frozen=True)
class PDFMagic:
    type: str
    version: str
    mime: str
    path: Path


class PDF:
    def magic(path: str) -> PDFMagic:
        with open(args.path, "rb") as file:
            header = file.readline().strip()  # remove newline
            if not header.startswith(b"%PDF"):
                raise BufferError("File is not a portable document format.")
            name, version = header.decode().split("-")
            type = name[1:].lower()
            mime = f"application/{type}"
            return PDFMagic(
                type=type,
                version=version,
                mime=mime,
                path=Path(path),
            )


# Usage example
if __name__ == "__main__":
    """
    Convert a PDF document into text and optionally save or print it.
    """

    from argparse import ArgumentParser, Namespace

    parser = ArgumentParser(
        description="Convert a PDF document into text and optionally save or print it."
    )
    parser.add_argument(
        "path",
        help="The path to the PDF document to be converted.",
    )
    parser.add_argument(
        "-o",
        "--output",
        type=str,
        default="",
        help="The path to save the extracted text. If not provided, the text will be printed to stdout.",
    )
    args = parser.parse_args()

    pdf_magic = pdf_magic_factory(args.path)
    print(pdf_magic)
    # print(packed[:30])
