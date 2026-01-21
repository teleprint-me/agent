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

from pdfminer.high_level import extract_text_to_fp
from pdfminer.layout import LAParams

# Usage example
if __name__ == "__main__":
    """
    Convert a PDF document into text and optionally save or print it.
    """

    from argparse import ArgumentParser, Namespace

    def parse_args() -> Namespace:
        parser = ArgumentParser(
            description="Convert a PDF document into text and optionally save or print it."
        )
        parser.add_argument(
            "-i",
            "--input_path",
            type=str,
            required=True,
            help="The path to the PDF document to be converted.",
        )
        parser.add_argument(
            "-o",
            "--output_path",
            type=str,
            default="",
            help="The path to save the extracted text. If not provided, the text will be printed to stdout.",
        )
        return parser.parse_args()

    args = parse_args()
    input_path = args.input_path
    output_path = args.output_path

    # Check if the input file exists and is a PDF
    if not os.path.isfile(input_path) or not input_path.endswith(".pdf"):
        print("Error: The input path must point to a valid PDF file.")
        exit(1)

    # Convert the PDF to text
    string = StringIO()
    params = LAParams()
    with open(args.input_path, "rb") as file:
        extract_text_to_fp(file, string, laparams=params, output_type="html", codec=None)
    content = string.getvalue()
    print(content)
