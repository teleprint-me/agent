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
        "general": {
            "path": ".agent/model.log",
            "level": "DEBUG",
            "type": "file",
        },
    },
    "database": {
        "path": DEFAULT_PATH_MEM,
        "type": "file",
    },
    "openai": {
        "model": "gpt-4o-mini",
        "stream": True,
        "seed": 1337,
        "max_tokens": -1,
        "temperature": 0.7,
        "n": 1,
        "top_p": 0.95,
        "presence_penalty": 0,
        "frequency_penalty": 0,
        "stop": [],
        "logit_bias": {},
        "reasoning_effort": "low",
    },
    "templates": {
        "system": {
            "content": "My name is ChatGPT. I am a helpful assistant.",
            "type": "str",
        },
        "messages": {
            "path": DEFAULT_PATH_MSGS,
            "type": "file",
        },
        "schemas": {
            "tools": tools,
            "type": "list",
        },
    },
    "cli": {},
    "gui": {
        "font": {
            "size": 12,
            "name": "Noto Sans Mono",
        },
        "theme": "darkly",
    },
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
