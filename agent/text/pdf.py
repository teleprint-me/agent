# agent/text/pdf.py
"""
Copyright (C) 2023 Austin Berrio

A Python script for converting PDF files to plaintext.
- https://en.wikipedia.org/wiki/PDF
- https://pdfminersix.readthedocs.io/en/latest/
"""

import os
from io import StringIO
from pathlib import Path
from typing import List, Union

from pdfminer.high_level import extract_pages, extract_text_to_fp
from pdfminer.layout import LAParams, LTPage, LTTextContainer

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

    # Check if the input file exists and is a PDF
    if not os.path.isfile(args.path) or not args.path.endswith(".pdf"):
        print("Error: The input path must point to a valid PDF file.")
        exit(1)

    # notes:
    # - not sure how to extract images yet
    # - there are no vertical boxes? only horizontal?
    # - box content is fine. no mods needed.
    # - vertical bands require manual buffers and mods.
    #   - a vertical band is a column of text containing a single character
    # - not sure how to extract tables yet.
    #   - tables end up flat and without structure.
    # - can be converted to html, but adds a lot of complexity.
    #   - tree-sitter could be used, but requires DOM-like traversal.
    #   - tags have no ids or classes to unique identify elements.
    #   - styles contain document coordinates, but do not render correctly.
    # - try to extract text using pdfminer first. then see how it goes from there.

    # Convert the PDF to text
    string = StringIO()
    params = LAParams()
    for page in extract_pages(args.path):  # LTPage
        print(f"Page: {page.pageid}")
        # LTLayoutContainer ? not sure which is base yet.
        # base could be LTContainer, LTComponent, or something else.
        # docs suggest isinstance to detect element types.
        for element in page:
            print(element)
            if hasattr(element, "get_text"):
                text = element.get_text()
                buffer = []  # vertical text
                for line in text.splitlines():
                    if len(line) == 1:  # discovered vertical band
                        buffer.append(line)
                if buffer:
                    # appended vertical elements are added in reverse order
                    # mirror the content to restore lexicographical order
                    text = "".join(reversed(buffer))
                print(text)
