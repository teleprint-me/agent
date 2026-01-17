# agent/text/html2markdown.py
"""
Copyright (C) 2023 Austin Berrio

A Python script for converting HTML files to Markdown format.

This script recursively processes files in the input directory, converting HTML documents to Markdown format. It employs BeautifulSoup and html2text libraries to clean HTML content and perform the conversion. The script also provides detailed logging for error handling during file operations.
"""

import os
import time
from logging import Logger
from pathlib import Path
from typing import Optional, Union

import html2text
import tqdm
from bs4 import BeautifulSoup

from agent.text.file import TextFile


def clean_code_blocks(html: str) -> str:
    """Clean up 'pre' blocks by removing 'a' tags within them."""
    soup = BeautifulSoup(html, "html.parser")

    for pre_tag in soup.find_all("pre"):
        for a_tag in pre_tag.find_all("a"):
            a_tag.replace_with(a_tag.text)

    return str(soup)


def convert_html_to_markdown(html: str) -> str:
    """Convert HTML content to Markdown format."""
    h = html2text.HTML2Text()

    h.body_width = 0  # No line wrapping
    h.single_line_break = True  # Single newlines turn into <br>
    h.ignore_links = True
    h.ignore_images = True
    h.ignore_tables = True
    h.escape_all = True  # Don't escape special characters

    return h.handle(html).strip()


def replace_code_tags_with_backticks(markdown_text: str) -> str:
    """Replace custom [code] tags with Markdown code block syntax."""
    return markdown_text.replace("[code]", "```").replace("[/code]", "```")


def process_html_content(html_content: str) -> str:
    """Process HTML content to clean and convert to Markdown."""
    cleaned_html = clean_code_blocks(html_content)
    # NOTE: Substitute anchor paths to maintain references
    markdown_content = convert_html_to_markdown(cleaned_html).replace(".html", ".md")
    # NOTE: Replacing code tags with backticks has inconsistent side effects.
    final_content = replace_code_tags_with_backticks(markdown_content)
    return final_content


def get_input_file_path(file_entry: Union[str, Path, os.DirEntry]) -> Path:
    pass


def get_output_file_path(
    input_file_path: Union[str, Path], output_dir: Union[str, Path]
) -> Path:
    """Generate the output file path with a .md extension."""
    output_file_name = Path(input_file_path).stem + ".md"
    return Path(output_dir) / output_file_name


def process_html_file_entry(
    file_entry: Union[str, Path, os.DirEntry],
    output_dir: Union[str, Path],
    dry_run: bool,
    logger: Logger,
    pbar: Optional[tqdm.tqdm] = None,
) -> None:
    """Process a file or directory entry and convert it from HTML to Markdown."""
    file_entry = Path(
        file_entry.path if isinstance(file_entry, os.DirEntry) else file_entry
    )
    output_dir = Path(
        os.path.join(output_dir, file_entry.path)
        if isinstance(file_entry, os.DirEntry)
        else os.path.join(output_dir, file_entry)
    )

    html_content = TextFile.read(file_entry)
    if html_content is None:
        logger.error(f"Failed to read {file_entry.name}. Skipping.")
        return

    markdown_content = process_html_content(html_content)

    if output_dir.is_file():
        raise ValueError("Expected a directory. Got a file instead.")

    output_file = get_output_file_path(file_entry, output_dir)

    if dry_run:
        logger.info(f"Would write {len(markdown_content)} bytes to {output_file}")
        return

    TextFile.write(output_file, markdown_content)

    if pbar:
        pbar.update(1)


def process_html_directory(
    input_dir: Union[str, Path],
    output_dir: Union[str, Path],
    n_threads: int,
    dry_run: bool,
    logger: Logger,
) -> None:
    logger.info("Starting directory processing.")
    start_time = time.time()
    file_entry_list = TextFile.collection(input_dir)
    TextFile.pool(
        file_entry_list,
        output_dir,
        process_html_file_entry,
        n_threads,
        dry_run,
        logger,
    )
    end_time = time.time()
    elapsed_time = end_time - start_time
    logger.info(f"Elapsed {elapsed_time:.2f} seconds using {n_threads} threads.")


if __name__ == "__main__":
    from argparse import ArgumentParser, Namespace

    from agent.config import config

    def parse_args() -> Namespace:
        parser = ArgumentParser(description="Convert HTML files to Markdown format.")
        parser.add_argument(
            "-i",
            "--input-path",
            required=True,
            default="",
            help="Path to the file or directory to process.",
        )
        parser.add_argument(
            "-o",
            "--output-dir",
            default="converted_md",
            help="Directory to the processed output.",
        )
        parser.add_argument(
            "-t",
            "--n-threads",
            type=int,
            default=os.cpu_count() or 4,
            help="Number of threads to use for processing.",
        )
        parser.add_argument(
            "-d",
            "--dry-run",
            default=False,
            action="store_true",
            help="Perform a dry run and fake generating the C and C++ raw dataset.",
        )
        parser.add_argument(
            "-v",
            "--verbose",
            action="store_true",
            help="Enable verbosity (Default: False).",
        )
        return parser.parse_args()

    args = parse_args()

    input_path = Path(args.input_path)
    output_path = Path(args.output_dir)

    logger = config.get_logger("logger", "html2markdown")
    if input_path.is_file():
        process_html_file_entry(
            file_entry=input_path,
            output_dir=output_path,
            dry_run=args.dry_run,
            logger=logger,
        )
    elif input_path.is_dir():
        process_html_directory(
            input_dir=input_path,
            output_dir=output_path,
            n_threads=args.n_threads,
            dry_run=args.dry_run,
            logger=logger,
        )
    else:
        print(f"Invalid input path: {input_path}. Exiting.")
