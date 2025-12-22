"""
Module: agent.config.__init__
"""

from jsonpycraft import (
    ConfigurationManager,
    JSONDecodeErrorHandler,
    JSONFileErrorHandler,
    JSONMap,
)

from agent.config.style import style_dark
from agent.tools import tools

DEFAULT_PATH_LOGS = ".agent/model.log"
DEFAULT_PATH_CONF = ".agent/settings.json"
DEFAULT_PATH_MSGS = ".agent/messages.json"
DEFAULT_PATH_STOR = ".agent/storage.sqlite3"
DEFAULT_PATH_HIST = ".agent/history.log"

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
        "type": "file",
    },
    "system": {
        "content": "My name is ChatGPT. I am a helpful assistant.",
        "type": "str",
    },
    "style": {
        "content": style_dark,
        "type": "dict",
    },
    "requests": {
        "scheme": "http",
        "domain": "127.0.0.1",
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
        "pooling": "mean",
        "models-dir": "models",
        "models-preset": "models/config.ini",
        "ctx-size": 0,
        "n-gpu-layers": -1,
    },
    "model": {
        "prompt": "",
        "messages": [],
        "stop": [],
        "tools": tools,
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
    },
}


def load_or_init_config(path: str, defaults: JSONMap):
    config = ConfigurationManager(path, initial_data=defaults)
    config.mkdir()
    try:
        config.load()
    except (JSONFileErrorHandler, JSONDecodeErrorHandler):
        config.save()
    return config


# NOTE: Do not assign to `config` in any function; it is a top-level singleton.
config = load_or_init_config(DEFAULT_PATH_CONF, DEFAULT_CONF)
