# agent/config/__init__.py
"""
This module provides configuration management for the agent framework.
It implements a singleton pattern for accessing global settings that define
sane defaults for users.

Configuration Management:
- Loads JSON files from .agent/*.json
- Supports environment variable overrides
- Allows runtime reloading of configurations
- Provides access to nested configuration values

Configuration Structure:
The default configuration defines settings for logging, history tracking,
database storage, message handling, system behavior, shell access, and
server parameters.

Example usage:
    # All values are accessed through a singleton instance
    config = ConfigurationManager(file_path, initial_data={"server": {}}, indent=2)
    config.set_value("server.models-dir", "/mnt/models")
    model_path = config.get_value("server.models-dir")   # -> "/mnt/models"
    # A logging.Logger instance can be created for each use case using a config key
    logger = config.get_logger(key="logger", logger_name="my_logger")
"""

from jsonpycraft import (
    ConfigurationManager,
    JSONDecodeErrorHandler,
    JSONFileErrorHandler,
    JSONMap,
)

from agent.config.style import style_dark
from agent.tools import tools

DEFAULT_PATH_CACH = ".agent"
DEFAULT_PATH_MSGS = f"{DEFAULT_PATH_CACH}/messages"
DEFAULT_PATH_CONF = f"{DEFAULT_PATH_CACH}/settings.json"
DEFAULT_PATH_LOGS = f"{DEFAULT_PATH_CACH}/data.log"
DEFAULT_PATH_HIST = f"{DEFAULT_PATH_CACH}/history.log"
DEFAULT_PATH_STOR = f"{DEFAULT_PATH_CACH}/storage.sqlite3"

DEFAULT_CONF = {
    "logger": {
        "path": DEFAULT_PATH_LOGS,
        "level": "DEBUG",
        "type": "file",
    },
    "history": {
        "path": DEFAULT_PATH_HIST,
        "type": "file",
    },
    "database": {
        "path": DEFAULT_PATH_STOR,
        "type": "file",
    },
    "messages": {
        "path": DEFAULT_PATH_MSGS,
        "type": "dir",
    },
    "system": {
        "content": "My name is ChatGPT. I am a helpful assistant.",
        "type": "str",
    },
    "style": {
        "content": style_dark,
        "type": "dict",
    },
    "terminal": {
        "shell": "/usr/bin/bash",
        "executable": False,
        "restricted": False,
        "command_names": [
            "date",
            "ls",
            "printf",
            "echo",
            "cat",
            "head",
            "tail",
            "wc",
            "grep",
            "find",
            "diff",
            "git",
        ],
    },
    "requests": {
        "scheme": "http",
        "host": "127.0.0.1",
        "port": "8080",
        "headers": {
            "Content-Type": "application/json",
        },
        "timeout": 30,
    },
    "server": {
        "metrics": True,
        "props": True,
        "slots": True,
        "jinja": True,
        "kv-unified": True,
        "verbose": False,
        "models-dir": "models",
        "pooling": "mean",
        "ctx-size": 0,
        "n-gpu-layers": -1,
    },
    "parameters": {
        "prompt": "",
        "messages": [],
        "stop": [],
        "chat_template_kwargs": {},
        "top_k": 50,
        "top_p": 0.90,
        "min_p": 0.1,
        "temperature": 0.8,
        "presence_penalty": 0.1,
        "frequency_penalty": 0.2,
        "repeat_penalty": 1.2,
        "n_predict": -1,
        "seed": 1337,
        "stream": True,
        "cache_prompt": True,
        "tools": tools,
    },
    "model": {
        "chat": "gpt-oss-20b-mxfp4",
        "embed": "qwen3-embedding-0.6b-q8_0",
        "complete": "llama32-instruct-1b-q8_0",
        "code": "qwen25-coder-1.5b-f16",
    },
}


def load_or_init_config(path: str, defaults: JSONMap) -> ConfigurationManager:
    """Initialize the configuration manager with default settings.

    Args:
        path: Path to the configuration file
        defaults: Default configuration values

    Returns:
        A ConfigurationManager instance initialized with the specified settings
    """
    config = ConfigurationManager(path, initial_data=defaults)

    try:
        config.mkdir()
        config.load()
    except (JSONFileErrorHandler, JSONDecodeErrorHandler):
        config.save()

    return config


# NOTE: Do not assign to `config` in any function; it is a top-level singleton.
config: ConfigurationManager = load_or_init_config(DEFAULT_PATH_CONF, DEFAULT_CONF)
