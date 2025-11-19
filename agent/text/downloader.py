"""
Copyright © 2025 Austin Berrio
Module: agent.text.downloader
Description: Downloads a file from a given source url to a destinatation path.

This is intentionally kept as simple as possible. The downloader times out after 30
seconds (which is the default) and it's allowed to raise an exception on failure. The
failure is reported to the user and the user is expected to manually intervene.

The TinyDataDownloader:
  - checks if the path exists to mitigate the need to list every possible exception.
  - creates a directory and its parent structure if it does not exist.
  - only supports plaintext, JSON, and parquet to keep things simple.
    - text is not restricted to `.txt` files and includes any valid unicode text file.
  - does not make any assumptions for the cached or returned data.
  - simplifies how progress is reported while downloading data.
This keeps the code lean and clean as a result.
"""

import json
import multiprocessing
import os
import random
import sys
import unicodedata
from time import sleep

import pandas as pd
import requests
from tiny.logger import TinyLogger
from tqdm import tqdm


class TextDownloader:
    def __init__(self, root_dir: str = "data", verbose: bool = False):
        os.makedirs(root_dir, exist_ok=True)
        self.dir = str(root_dir)
        self.encoding = "utf-8"
        self.logger = TinyLogger.get_logger(self.__class__.__name__, verbose)
        self.bar_format = (
            "[{desc}: {percentage:3.0f}%] "
            "[{n_fmt}/{total_fmt}] "
            "[{rate_fmt}{postfix}] "
            "[{elapsed}]"
        )

    def download_file(
        self,
        source_url: str,
        source_file: str,
        rate_limit: float = 0.0,
        position: int = None,
    ) -> bool:
        """
        Downloads a file from a given URL and saves it locally.
        Returns True if successful, False otherwise.
        """

        try:
            self.logger.debug(f"Downloading '{source_file}' from '{source_url}'.")

            sleep(rate_limit)  # Be kind to servers!
            response = requests.get(source_url, stream=True, timeout=30)
            response.raise_for_status()

            kwargs = {
                "total": int(response.headers.get("content-length", 0)),
                "unit": "B",
                "unit_scale": True,
                "position": position,
                "bar_format": self.bar_format,
                "disable": not sys.stdout.isatty(),
            }
            with tqdm(**kwargs) as pbar:
                os.makedirs(
                    os.path.dirname(source_file), exist_ok=True
                )  # Ensure directory exists
                with open(source_file, "wb") as file:
                    for data in response.iter_content(1024):
                        pbar.update(len(data))
                        file.write(data)

            return True  # Success
        except Exception as e:
            self.logger.error(
                f"Failed to download '{source_file}' from '{source_url}': {e}"
            )
            return False  # Failure

    # IMPORTANT: https://stackoverflow.com/a/46398645/15147156
    def download_list(
        self,
        source_list: list[dict[str, str]],
        rate_limit: float = 0.35,
        min_stagger: float = 0.01,
        max_stagger: float = 0.1,
    ) -> None:
        """Downloads a listed set of source files from a set of source URLs using multiprocessing."""

        random.shuffle(source_list)  # Reduce predictable access patterns

        num_workers = min(multiprocessing.cpu_count(), len(source_list))

        # Compute final staggered delays
        staggered_limits = [
            round(rate_limit + random.uniform(min_stagger, max_stagger), 3)
            for _ in source_list
        ]
        self.logger.info(f"Downloading list with timeouts: {staggered_limits}")

        # Assign delays dynamically
        sources = [
            (
                source["url"],
                source["file"],
                staggered_limits[position],  # Use precomputed stagger
                position,
            )
            for position, source in enumerate(source_list)
        ]

        with multiprocessing.Pool(processes=num_workers) as pool:
            results = pool.starmap(self.download_file, sources)

        processed = sum(results)  # Count successful downloads
        failed = len(results) - processed  # Count failed downloads

        self.logger.info(f"Processed: {processed}, Failed: {failed}")

    def read_text(self, source_file: str) -> str:
        """Read and normalize a plaintext file to unicode utf-8."""

        with open(source_file, "r", encoding=self.encoding) as file:
            text = file.read()
        return unicodedata.normalize("NFKC", text)  # Normalize the text

    def read_json(self, source_file: str) -> any:
        """Read and normalize a JSON file to unicode utf-8."""

        with open(source_file, "r", encoding=self.encoding) as file:
            return json.load(file)

    def read_parquet(self, source_file: str) -> any:
        """Read a parquet file."""

        return pd.read_parquet(source_file)

    def read_file(self, source_file: str, file_type: str) -> any:
        """Read a supported file type into memory."""

        if file_type not in {"text", "json", "parquet"}:
            raise ValueError(f"Unsupported file type: {file_type}")

        self.logger.debug(f"Reading '{file_type}' for '{source_file}'.")

        read = {
            "text": self.read_text,
            "json": self.read_json,
            "parquet": self.read_parquet,
        }[file_type]

        return read(source_file)

    def read_or_download(
        self, source_url: str, source_file: str, file_type: str = "text"
    ) -> any:
        """Read cached file type if available, otherwise download it."""
        # Check if the cached path exists
        if os.path.exists(source_file):
            return self.read_file(source_file, file_type)

        # Otherwise cache the path
        self.download_file(source_url, source_file)
        return self.read_file(source_file, file_type)
