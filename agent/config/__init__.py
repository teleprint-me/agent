"""
Module: agent.config.__init__
"""

from jsonpycraft import (
    ConfigurationManager,
    JSONDecodeErrorHandler,
    JSONFileErrorHandler,
    JSONMap,
)

from agent.tools import tools

DEFAULT_PATH_CONF = ".agent/settings.json"
DEFAULT_PATH_MSGS = ".agent/messages.json"
DEFAULT_PATH_MEM = ".agent/storage.sqlite3"

DEFAULT_CONF = {
    "logger": {
        "path": ".agent/model.log",
        "level": "DEBUG",
        "type": "file",
    },
    "database": {
        "path": DEFAULT_PATH_MEM,
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
    "server": {
        "base_url": "http://127.0.0.1",
        "port": 8080,
        "ctx-size": -1,
        "n-gpu-layers": 99,
        "slots": False,
        "jinja": False,
        "embeddings": False,
        "pooling": "none",
        "verbose": False,
        "timeout": 30,
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
        "presence_penalty": 0.0,
        "frequency_penalty": 0.0,
        "repeat_penalty": 1.1,
        "n_predict": -1,
        "seed": 1337,
        "stream": True,
        "cache_prompt": True,
    },
    "cli": {},
    # Add other sections as needed
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
