"""
text_extraction/pdf.py

A Python script for converting PDF files to plaintext.

Copyright (C) 2024 Austin Berrio
"""

import argparse
import os
from pathlib import Path
from typing import List, Union

from poppler import load_from_file


def convert_pdf_to_text(file_name: Union[str, Path]) -> List[str]:
    """
    Convert a PDF document into a list of strings, where each string represents the text of a page.

    Args:
        file_name (Union[str, Path]): The path to the PDF file to be converted.

    Returns:
        List[str]: A list of strings representing the text of each page in the PDF.
    """
    pages: List[str] = []
    pdf_document = load_from_file(file_name=file_name)
    for index in range(pdf_document.pages):
        page = pdf_document.create_page(index)
        pages.append(page.text())
    return pages


def get_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
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


def main(args: argparse.Namespace):
    """
    Convert a PDF document into text and optionally save or print it.
    """
    input_path = args.input_path
    output_path = args.output_path

    # Check if the input file exists and is a PDF
    if not os.path.isfile(input_path) or not input_path.endswith(".pdf"):
        print("Error: The input path must point to a valid PDF file.")
        exit(1)

    # Convert the PDF to text
    pages = convert_pdf_to_text(input_path)

    # Save or print the extracted text
    if output_path:
        with open(output_path, "a+") as text_file:
            for page in pages:
                text_file.write(page)
    else:
        for page in pages:
            print(page)


if __name__ == "__main__":
    args = get_arguments()
    main(args)
