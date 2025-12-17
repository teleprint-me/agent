"""
Module: agent.hf.download

Docs:
    # NOTE: Manual model downloading is limited and error prone.
    - https://huggingface.co/docs/hub/models-downloading
    # NOTE: Automated downloading is recommended for larger models.
    - https://huggingface.co/docs/huggingface_hub/main/en/package_reference/file_download

User Access Token:
    - https://huggingface.co/settings/tokens

NOTE: This is still a Work in Progress.
"""

import logging
import sys
from concurrent import futures
from logging import Logger
from pathlib import Path
from typing import List, Optional, Union

from agent.hf.logger import get_default_logger
from huggingface_hub import (
    HfApi,
    dataset_info,
    hf_hub_download,
    login,
    model_info,
    space_info,
)
from huggingface_hub.errors import (
    EntryNotFoundError,
    LocalEntryNotFoundError,
    RepositoryNotFoundError,
)


class HuggingFaceDownload:
    def __init__(
        self,
        token: Optional[str] = None,
        logger: Optional[Logger] = None,
    ):
        """
        Initializes the HuggingFaceDownload object.

        Args:
            token (str, optional): The Hugging Face API token for remote authentication.
            logger (Logger, optional): A custom logger instance for logging, if provided.

        Notes:
            - The implementation details regarding remote authentication are confusing.
            - Hugging Face "supports" multiple options for remote authentication, but
              the actual functionality is unclear.
            - Despite the `token` argument, HfApi's constructor is not respected for
              authentication, leading to potential errors.
            - There were multiple attempts to authenticate, and it's unclear which one
              will function as expected.
            - The documentation and implementation details seem to contradict each other,
              causing frustration and confusion.
        """
        # Authenticate with the Hugging Face API using the provided token
        login(token, add_to_git_credential=False)

        # Initialize the Hugging Face API client
        self.api = HfApi()

        # Store the token for reference in download_file method
        self.token = token

        # Initialize the logger
        if logger:
            self._logger = logger
        else:
            self._logger = get_default_logger(self.__class__.__name__, logging.INFO)

    def download_file(
        self,
        local_file: str,
        local_path: str,
        repo_id: str,
        repo_type: Optional[str] = None,
        force_download: bool = False,
    ) -> str:
        model_path = hf_hub_download(
            repo_id=repo_id,
            filename=local_file,
            repo_type=repo_type,
            local_dir=local_path,
            force_download=force_download,
            token=self.token,  # Input token is not respected
        )
        self._logger.info(f"Downloaded {local_file} to {model_path}")
        return model_path

    def _download_all_files(
        self,
        repo_id: str,
        local_path: str,
        local_files: List[str],
        repo_type: Optional[str] = None,
        force_download: bool = False,
    ) -> List[str]:
        """Download a list of files in parallel."""

        def _worker(file_name: str) -> str:
            return self.download_file(
                local_file=file_name,
                local_path=local_path,
                repo_id=repo_id,
                repo_type=repo_type,
                force_download=force_download,
            )

        max_workers = min(8, len(local_files))
        results = []
        with futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
            results = list(executor.map(_worker, local_files))
        return results

    def download_folder(
        self,
        local_path: str,
        repo_id: str,
        repo_type: Optional[str] = None,
        force_download: bool = False,
    ) -> None:
        # NOTE: Consider resetting `retries` to zero if a retry is successful.
        self._logger.info(f"Using {repo_id} to download source data.")
        retries = 0
        max_retries = 3

        try:
            if repo_type == "dataset":
                metadata = dataset_info(repo_id)
            elif repo_type == "space":
                metadata = space_info(repo_id)
            else:
                metadata = model_info(repo_id)

            local_files = []
            for x in metadata.siblings:
                filename = x.rfilename
                # NOTE: Ignore consolidated files to enforce dedupping
                if filename.startswith("consolidated"):
                    continue
                # NOTE: Ignore hidden files
                if filename[0] == ".":
                    continue  # ignore .cache, etc.
                local_files.append(filename)

            self._download_all_files(
                repo_id=repo_id,
                local_path=local_path,
                local_files=local_files,
                repo_type=repo_type,
                force_download=force_download,
            )
        except (EntryNotFoundError, RepositoryNotFoundError) as e:
            self._logger.error(f"Error downloading source: {e}")
            sys.exit(1)
        except LocalEntryNotFoundError as e:
            self._logger.error(f"Error accessing source: {e}")
            while retries < max_retries:
                self._logger.info("Retrying download...")
                retries += 1
                self._download_all_files(
                    repo_id,
                    local_path,
                    local_files,
                    repo_type,
                    force_download,
                )
        except Exception as e:
            self._logger.error(f"Error downloading source: {e}")
            sys.exit(1)

    def download(
        self,
        path: Union[str, Path],
        repo_id: str,
        repo_type: Optional[str] = None,
        force_download: bool = False,
        is_file: bool = False,
    ):
        """
        Download files or directories from a Hugging Face repository.
        """
        # Convert path to a Path object for consistency
        path_obj = Path(path) if isinstance(path, str) else path

        # Create the parent directory if it doesn't exist
        self._logger.info(
            f"Downloading to {'file' if is_file else 'directory'}: {path_obj}"
        )

        if is_file:
            path_obj.parent.mkdir(parents=True, exist_ok=True)
            file_name = path_obj.name
            local_path = path_obj.parent
            self.download_file(
                local_file=file_name,
                local_path=str(local_path),
                repo_id=repo_id,
                repo_type=repo_type,
                force_download=force_download,
            )
        else:
            path_obj.mkdir(parents=True, exist_ok=True)
            self.download_folder(
                local_path=str(path_obj),
                repo_id=repo_id,
                repo_type=repo_type,
                force_download=force_download,
            )
