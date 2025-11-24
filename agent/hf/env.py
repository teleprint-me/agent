"""
Module: agent.hf.env
"""

import os
from typing import Optional

import dotenv


def get_environment(
    file_path: Optional[str] = None, variable: Optional[str] = None
) -> str:
    """
    Get the value of an environment variable.

    Args:
        variable (str, optional): The name of the environment variable. Defaults to "OPENAI_API_KEY".

    Returns:
        str: The value of the environment variable.
    """
    file_path = ".env" if file_path is None else file_path
    variable = "HUGGINGFACE_READ_API" if variable is None else variable

    if not dotenv.load_dotenv(file_path):
        raise ValueError("EnvironmentError: Failed to load `.env`")

    value = os.getenv(variable) or ""

    if not value:
        raise ValueError(f"EnvironmentError: Failed to find `{variable}`")

    return value
