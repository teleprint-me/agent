"""
Module: agent.text.file

Copyright (C) 2024 Austin Berrio
"""

import logging
import os
from concurrent.futures import ThreadPoolExecutor
from logging import Logger
from pathlib import Path
from typing import Callable, List, Optional, Union

import tqdm

from agent.text.logger import TextLogger

HTMLProcess = Callable[
    [
        os.DirEntry,
        Union[str, Path],
        bool,
        Logger,
        Optional[tqdm.tqdm],
    ],
    None,
]


class TextFile:
    @staticmethod
    def read(file_path: Union[str, Path]) -> Optional[str]:
        """Read content from a source file."""
        try:
            with open(file_path, "r") as f:
                return f.read()
        except Exception as e:
            TextLogger.get_logger(__name__, logging.ERROR).error(
                f"An error occurred while reading from the source file: {e}"
            )
        return None

    @staticmethod
    def write(file_path: Union[str, Path], content: str) -> None:
        """Write content to a destination file."""
        try:
            os.makedirs(os.path.dirname(file_path), exist_ok=True)
            with open(file_path, "w") as f:
                f.write(content)
        except Exception as e:
            TextLogger.get_logger(__name__, logging.ERROR).error(
                f"An error occurred while writing to the destination file: {e}"
            )

    @staticmethod
    def collection(dir_entry: Union[str, os.DirEntry]) -> List[os.DirEntry]:
        """Collect all file entries in a directory recursively."""
        file_entry_list = []
        dir_entry_path = (
            dir_entry.path if isinstance(dir_entry, os.DirEntry) else dir_entry
        )
        for entry in os.scandir(dir_entry_path):
            if entry.is_file():
                file_entry_list.append(entry)
            elif entry.is_dir():
                file_entry_list.extend(TextFile.collection(entry))
        return file_entry_list

    @staticmethod
    def pool(
        file_entry_list: List[os.DirEntry],
        output_dir: Union[str, Path],
        process_entry: HTMLProcess,
        n_threads: int,
        dry_run: bool,
        logger: Logger,
    ) -> None:
        with ThreadPoolExecutor(max_workers=n_threads) as executor:
            with tqdm.tqdm(total=len(file_entry_list)) as pbar:
                for _ in executor.map(
                    lambda file_entry: process_entry(
                        file_entry,
                        output_dir,
                        dry_run,
                        logger,
                        pbar,
                    ),
                    file_entry_list,
                ):
                    pass
