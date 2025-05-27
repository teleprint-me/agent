"""
Module: agent.cli.config
"""

from jsonpycraft import (
    ConfigurationManager,
    JSONDecodeErrorHandler,
    JSONFileErrorHandler,
    JSONMap,
)

from agent.tools import tools

DEFAULTS = {
    "openai": {
        "system": "My name is ChatGPT. I am a helpful assistant.",
        "model": "gpt-3.5-turbo",
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
        "tools": tools,
    },
    "messages": {
        "path": ".agent/cli/messages.json",
    },
    # Add other sections as needed
}


def load_or_init_config(path: str, defaults: JSONMap, indent: int = 2):
    config = ConfigurationManager(path, initial_data=defaults, indent=indent)
    config.mkdir()
    try:
        config.load()
    except (JSONFileErrorHandler, JSONDecodeErrorHandler):
        config.save()
    return config


config = load_or_init_config(".agent/cli/settings.json", DEFAULTS)
